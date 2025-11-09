from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from ..services.core_service import check_student_exists, execute_delete_students, get_student_ID_by_face, check_access_of_student, execute_insert_student, update_student, process_access_record, create_reservation, check_time, get_access_records, get_seat_information, check_time_overlap, get_reservation_status, check_student_inside
from ..utils.helper_functions import error_response, success_response, format_db_rows_to_json, validate_input


router = APIRouter()

# 1. 출입 기록 확인 핸들러
@router.get("/list")
async def get_access_list_handler(
    sid: Optional[str] = Query(None), start_date: Optional[str] = Query(None), end_date: Optional[str] = Query(None)
):
    
    input_data = {
        'sid': sid, 
        'start_date': start_date, 
        'end_date': end_date
    }
    input_data = {k: v for k, v in input_data.items() if v is not None}

    # 1. 입력된 조건의 형식 유효성 확인 (400 방어)
    # if not validate_input(sid=sid, start_date=start_date, end_date=end_date):
    #     raise HTTPException(status_code=400, detail="INVALID_FORMAT")
        
    # 2. 조건에 맞는 기록 조회 (SELECT)
    result = get_access_records(sid=sid, start_date=start_date, end_date=end_date)
    
    # 500 DB 실행 오류 확인
    if isinstance(result, tuple) and not result[0]:
        raise HTTPException(status_code=500, detail="DB_ERROR")
        
    # 3. DB Row 객체를 JSON 리스트로 변환 (포장)
    access_list = format_db_rows_to_json(result)

    # 4. 성공 응답 반환 (기록이 없어도 200 OK)
    return success_response(message="ACCESS_LIST_RETURN", status_code=200, data=access_list)




# 3. 인증 성공 시 출입 상태를 DB에 기록 남기기

@router.post("/record")
async def record_access_handler(data: Dict[str, Any]):
    
    # 값 추출 및 필수 입력값 확인
    sid = data.get('sid')
    required_keys = ['sid']
    
    if not validate_input(data, required_keys): 
        raise HTTPException(status_code=400, detail="EMPTY_DATA")
    
    # 회원 존재 여부 확인
    if not check_student_exists(sid):
         raise HTTPException(status_code=404, detail="NOT_FOUND")

    
    # 해당되는 회원의 최근 출입 기록 조회
    recent_log = get_access_records(sid) 

    if recent_log:
        # DB Row 리스트에서 가장 최근 기록(첫 번째 항목)을 꺼냅니다.
        most_recent_row = recent_log[0]
        
        # sqlite3.Row 객체를 check_access_of_student 함수가 원하는 딕셔너리로 변환하여 재할당합니다.
        recent_log = most_recent_row
    else:
        # 기록이 없으면 (빈 리스트이면) check_access_of_student 함수의 Optional[Dict] 타입 힌트에 맞춰 None을 할당합니다.
        recent_log = None
    
    # 상태 판단
    # action_type: 'IN' 또는 'OUT'
    # log_id: OUT일 경우 UPDATE할 대상 ID
    action_type, update_log_id = check_access_of_student(recent_log)
    
    if action_type is None:
        raise HTTPException(status_code=409, detail="WRONG_POSITION_LIBRARY")

    
    # 출입 기록 최종 저장
    success, error_details = process_access_record(sid, action_type, update_log_id)
    
    if not success:
        raise HTTPException(status_code=500, detail=error_details.get('error_code'))
        
    
    # 성공 응답 반환
    message = f"ACCESS_RECORD_SUCCESS: {action_type} recorded"
    return success_response(
        message=message, 
        status_code=201
    )