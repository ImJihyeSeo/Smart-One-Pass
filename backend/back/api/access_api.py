from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from ..services.core_service import check_student_exists, get_student_ID_by_face, check_access_of_student, process_access_record, get_access_records
from ..utils.helper_functions import success_response, format_db_rows_to_json, validate_input
import numpy as np

router = APIRouter()

# 1. 출입 기록 확인 핸들러
@router.get("/list")
async def get_access_list_handler(
    sid: Optional[str] = Query(None), start_date: Optional[str] = Query(None), end_date: Optional[str] = Query(None)
):
    
    # 1. 입력된 조건의 형식 유효성 확인 (400 방어)
    # if not validate_input(sid=sid, start_date=start_date, end_date=end_date):
    #     raise HTTPException(status_code=400, detail="INVALID_FORMAT")
    
    input_data = {
        'sid': sid, 
        'start_date': start_date, 
        'end_date': end_date
    }
    input_data = {k: v for k, v in input_data.items() if v is not None}
        
    # 1) 조건에 맞는 기록 조회
    result = get_access_records(sid=sid, start_date=start_date, end_date=end_date)
    
    if isinstance(result, tuple) and not result[0]:
        raise HTTPException(status_code=500, detail="DB_ERROR")
        
    # 2) DB Row 객체를 JSON 리스트로 변환
    access_list = format_db_rows_to_json(result)

    # 3) 성공 응답 반환
    return success_response(message="ACCESS_LIST_RETURN", status_code=200, data=access_list)




# 2. 인증 성공 시 출입 상태를 DB에 기록 남기기
@router.post("/record")
async def record_access_handler(data: Dict[str, Any]):
    
    sid = data.get('sid')
    required_keys = ['sid']
    
    if not validate_input(data, required_keys): 
        raise HTTPException(status_code=400, detail="EMPTY_DATA")
    
    if not check_student_exists(sid):
         raise HTTPException(status_code=404, detail="NOT_FOUND")

    recent_log = get_access_records(sid) 

    if recent_log:
        most_recent_row = recent_log[0]
        
        recent_log = most_recent_row
    else:
        recent_log = None
    
    action_type, update_log_id = check_access_of_student(recent_log)
    
    if action_type is None:
        raise HTTPException(status_code=409, detail="WRONG_POSITION_LIBRARY")

    
    success, error_details = process_access_record(sid, action_type, update_log_id)
    
    if not success:
        raise HTTPException(status_code=500, detail=error_details.get('error_code'))
        
    
    message = f"ACCESS_RECORD_SUCCESS: {action_type} recorded"
    return success_response(
        message=message, 
        status_code=201
    )


# 3. 얼굴 인식 처리
@router.post("/identify")
async def identify_user_handler(data: Dict[str, Any]):
    """
    [API] 얼굴 벡터(임베딩)를 받아서 누구인지 식별(Identify)하여 반환
    """
    # 1) 클라이언트가 보낸 임베딩
    embedding_list = data.get("embedding")
    
    if not embedding_list:
        raise HTTPException(status_code=400, detail="EMPTY_EMBEDDING")

    try:
        # 2) 리스트를 바이트(bytes)로 변환
        emb_array = np.array(embedding_list, dtype=np.float32)
        emb_bytes = emb_array.tobytes()
        
        # 3) DB에서 누구인지 찾기
        result = get_student_ID_by_face(emb_bytes)
        
        if isinstance(result, tuple) and result[0] is False:
             return success_response(message="IDENTIFY_FAIL", status_code=200, data={"found": False})

        found_sid = result
        return success_response(
            message="IDENTIFY_SUCCESS", 
            status_code=200, 
            data={"found": True, "sid": found_sid}
        )
        
    except Exception as e:
        print(f"Identify Error: {e}")
        raise HTTPException(status_code=500, detail="SERVER_ERROR")