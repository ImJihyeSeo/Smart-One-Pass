# api/user_api.py (회원 정보 수정 및 삭제, 조회)
from fastapi import APIRouter, HTTPException, status, Query
from typing import Dict, Any, Optional

from database import get_db_connection, initialize_db
from ..services.core_service import check_student_exists, execute_delete_students, get_student_ID_by_face, check_access_of_student, execute_insert_student, update_student, process_access_record, create_reservation, check_time, get_access_records, get_seat_information, check_time_overlap, get_reservation_status, check_student_inside
from ..utils.helper_functions import error_response, success_response, format_db_rows_to_json, validate_input
# services 및 utils 폴더에서 필요한 함수들을 모두 import 가정

router = APIRouter()


# --- 회원 정보 등록 핸들러 (POST /user/register) ---
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user_handler(data: Dict[str, Any]):
    """
    새로운 학생 회원 정보를 등록합니다.
    """
    
    # 1. JSON 필수값 누락 확인 (400 Bad Request 방어)
    # 회원 등록 시 sid는 필수이며, face 또는 card 중 하나는 반드시 있어야 합니다.
    REQUIRED_KEYS = ['sid']
    validation_result = validate_input(data, REQUIRED_KEYS)
    
    # sid가 없거나, sid는 있지만 face와 card가 모두 누락된 경우
    if validation_result is not True or (not data.get('face') and not data.get('card')):
        
        # validate_input 실패 시의 상세 오류 메시지를 사용합니다.
        if validation_result is not True:
            _, error_detail = validation_result
        else:
            # face와 card가 모두 누락된 경우의 오류 메시지 (별도 정의)
            error_detail = {"error_code": "EMPTY_DATA", "message": "학번과 함께 얼굴 데이터 또는 카드 ID 중 하나는 필수입니다."}
            
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(
                error_code=error_detail['error_code'], 
                message=error_detail['message']
            )
        )
    
    sid = data.get('sid')
    face_data = data.get('face')
    card_id = data.get('card')
    
    # 2. 회원 존재 중복 확인 (409 Conflict 방어)
    if check_student_exists(sid):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_response(
                error_code="ALREADY_EXIST_USER",
                message=f"학번 {sid}는 이미 등록된 회원입니다."
            )
        )

    # 3. 회원 기록 최종 저장 (INSERT 트랜잭션 실행)
    # execute_insert_student 함수는 face_data가 bytes 타입이라고 가정합니다.
    success, error_details = execute_insert_student(sid, face_data, card_id)
    
    if not success:
        # DB 저장 중 오류 발생 시 (500 Internal Server Error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                error_code="DB_ERROR",
                message=f"회원 정보 등록 중 내부 데이터베이스 오류가 발생했습니다. 상세: {error_details.get('message', '알 수 없음')}"
            )
        )
        
    # 4. 성공 응답 반환 (201 Created)
    return success_response(
        message="USER_REGISTER_SUCCESS",
        status_code=status.HTTP_201_CREATED,
        data={"sid": sid} # 생성된 리소스의 식별자를 포함하여 반환
    )

# --- 회원 정보 수정 핸들러 (POST /user/update) ---
@router.post("/update")
async def update_user_handler(data: Dict[str, Any]):
    sid = data.get('sid')
    
    # 1. 필수값 유효성 검사 (400 방어)
    required_id = ['sid']
    if not validate_input(data, required_id) or (not data.get('face') and not data.get('card')):
        raise HTTPException(status_code=400, detail="EMPTY_DATA")
        
    # 2. 회원 존재 여부 확인 (404 방어)
    if not check_student_exists(sid):
        raise HTTPException(status_code=404, detail="NOT_FOUND")

    # 3. 수정 데이터 준비 및 실행 (UPDATE)
    update_data = {k: v for k, v in data.items() if k in ['face', 'card']}
    
    success, error_details = update_student(sid, update_data)
    if not success:
        raise HTTPException(status_code=500, detail=error_details.get('error_code'))
        
    return success_response(message="USER_UPDATE_SUCCESS", status_code=201)

# --- 회원 정보 삭제 핸들러 (POST /user/delete) ---
@router.post("/delete")
async def delete_user_handler(data: Dict[str, Any]):
    face_data = data.get('face')
    
    # 1. 얼굴 데이터 필수값 확인 (400 방어)
    if not validate_input(data, ['face']): 
        raise HTTPException(status_code=400, detail="EMPTY_DATA")
    
    # 2. 얼굴 데이터로 SID 찾기 및 인증 (404 방어)
    result = get_student_ID_by_face(face_data)
    if isinstance(result, tuple):
        raise HTTPException(status_code=404, detail=result[1].get('error_code'))
    
    sid_to_delete = result # 인증된 sid
    
    # 3. 회원 기록 삭제 (4단계 DELETE 트랜잭션 - 500 방어)
    if not execute_delete_students(sid_to_delete):
        raise HTTPException(status_code=500, detail="DB_ERROR")
        
    return success_response(message="USER_DELETE_SUCCESS", status_code=201)

# # --- 회원 정보 확인 핸들러 (GET /user/info) ---
# @router.get("/info")
# async def get_user_info_handler(sid: str = Query(..., description="조회할 회원의 학번 (SID)")):
    
#     # 1. 대상 회원 정보 조회 (SELECT)
#     user_data = get_user_info(sid) 
    
#     if user_data is None:
#         raise HTTPException(status_code=404, detail="NOT_FOUND")

#     # 2. 성공 응답 반환
#     return success_response(message="USER_INFO_SUCCESS", status_code=200, data=user_data)