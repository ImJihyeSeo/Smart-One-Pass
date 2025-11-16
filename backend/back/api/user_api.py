# api/user_api.py (회원 정보 수정 및 삭제, 조회)
from fastapi import APIRouter, HTTPException, status, Query
from typing import Dict, Any, Optional

# from database import get_db_connection, initialize_db
from ..services.core_service import check_student_exists, execute_delete_students, get_student_ID_by_face, check_access_of_student, execute_insert_student, update_student, process_access_record, create_reservation, check_time, get_access_records, get_seat_information, check_time_overlap, get_reservation_status, check_student_inside, prev_check_student
from ..utils.helper_functions import error_response, success_response, format_db_rows_to_json, validate_input
# services 및 utils 폴더에서 필요한 함수들을 모두 import 가정

router = APIRouter()


# --- 회원 정보 등록 핸들러 (POST /user/register) ---
# @router.post("/register", status_code=status.HTTP_201_CREATED)
# async def register_user_handler(data: Dict[str, Any]):
#     """
#     새로운 학생 회원 정보를 등록합니다.
#     """
    
#     # 1. JSON 필수값 누락 확인 (400 Bad Request 방어)
#     # 회원 등록 시 sid는 필수이며, face 또는 card 중 하나는 반드시 있어야 합니다.
#     REQUIRED_KEYS = ['sid']
#     validation_result = validate_input(data, REQUIRED_KEYS)
    
#     # sid가 없거나, sid는 있지만 face와 card가 모두 누락된 경우
#     if validation_result is not True or (not data.get('face') and not data.get('card')):
        
#         # validate_input 실패 시의 상세 오류 메시지를 사용합니다.
#         if validation_result is not True:
#             _, error_detail = validation_result
#         else:
#             # face와 card가 모두 누락된 경우의 오류 메시지 (별도 정의)
#             error_detail = {"error_code": "EMPTY_DATA", "message": "학번과 함께 얼굴 데이터 또는 카드 ID 중 하나는 필수입니다."}
            
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=error_response(
#                 error_code=error_detail['error_code'], 
#                 message=error_detail['message']
#             )
#         )
    
#     sid = data.get('sid')
#     face_data = data.get('face')
#     card_id = data.get('card')
    
#     # 2. 회원 존재 중복 확인 (409 Conflict 방어)
#     if check_student_exists(sid):
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail=error_response(
#                 error_code="ALREADY_EXIST_USER",
#                 message=f"학번 {sid}는 이미 등록된 회원입니다."
#             )
#         )

#     # 3. 회원 기록 최종 저장 (INSERT 트랜잭션 실행)
#     # execute_insert_student 함수는 face_data가 bytes 타입이라고 가정합니다.
#     success, error_details = execute_insert_student(sid, face_data, card_id)
    
#     if not success:
#         # DB 저장 중 오류 발생 시 (500 Internal Server Error)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=error_response(
#                 error_code="DB_ERROR",
#                 message=f"회원 정보 등록 중 내부 데이터베이스 오류가 발생했습니다. 상세: {error_details.get('message', '알 수 없음')}"
#             )
#         )
        
#     # 4. 성공 응답 반환 (201 Created)
#     return success_response(
#         message="USER_REGISTER_SUCCESS",
#         status_code=status.HTTP_201_CREATED,
#         data={"sid": sid} # 생성된 리소스의 식별자를 포함하여 반환
#     )

import base64 # 🚨 추가: face 데이터를 bytes로 변환하기 위해 필요

# ... (다른 import 생략)
# from core_service import check_student_exists, execute_insert_student
# from utils.helper_functions import validate_input, error_response, success_response

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user_handler(data: Dict[str, Any]):
    """
    새로운 학생 회원 정보를 등록합니다. (sid, name 필수, face 선택)
    """
    
    # 1. JSON 필수값 누락 확인 (400 Bad Request 방어)
    # 🚨 수정: sid와 name은 필수입니다. face 데이터는 선택입니다.
    REQUIRED_KEYS = ['sid', 'name']
    validation_result = validate_input(data, REQUIRED_KEYS)
    
    # name 또는 sid가 누락된 경우
    if validation_result is not True:
        _, error_detail = validation_result
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(
                error_code=error_detail['error_code'], 
                message=error_detail['message']
            )
        )
        
    # 🚨 추가: sid와 name은 필수지만, face 데이터가 완전히 없을 경우 DB 삽입 전 방어 로직
    # (선택적으로 face가 없더라도 등록은 가능하나, face가 있을 경우에만 변환)
    sid = data.get('sid')
    name = data.get('name') # 🚨 추가: name 데이터 추출
    
    # 2. face 데이터 처리
    # Postman에서 받은 Base64 문자열을 PostgreSQL BYTEA 타입을 위한 bytes 객체로 변환합니다.
    face_data = None
    face_data_base64 = data.get('face')
    
    if face_data_base64:
        try:
            face_data = base64.b64decode(face_data_base64)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response(
                    error_code="INVALID_BASE64",
                    message="제공된 얼굴 데이터(face)가 유효한 Base64 형식이 아닙니다."
                )
            )
            
    # 3. 회원 존재 중복 확인 (409 Conflict 방어)
    if check_student_exists(sid):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_response(
                error_code="ALREADY_EXIST_USER",
                message=f"학번 {sid}는 이미 등록된 회원입니다."
            )
        )

    # 4. 회원 기록 최종 저장 (INSERT 트랜잭션 실행)
    # 🚨 수정: execute_insert_student(sid, name, face_data) 형태로 호출 매개변수 변경
    success, error_details = execute_insert_student(sid, name, face_data)
    
    if not success:
        # DB 저장 중 오류 발생 시 (500 Internal Server Error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                error_code="DB_ERROR",
                message=f"회원 정보 등록 중 내부 데이터베이스 오류가 발생했습니다. 상세: {error_details.get('message', '알 수 없음')}"
            )
        )
        
    # 5. 성공 응답 반환 (201 Created)
    return success_response(
        message="USER_REGISTER_SUCCESS",
        status_code=status.HTTP_201_CREATED,
        data={"sid": sid, "name": name} # 생성된 리소스의 식별자를 포함하여 반환
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
    # update_data = {k: v for k, v in data.items() if k in ['face', 'card']}
    # 3. 수정 데이터 준비 및 실행 (UPDATE)
    update_data = {}
    
    # 🚨 수정: face 데이터 디코딩 로직 추가
    if 'face' in data:
        face_base64 = data['face']
        try:
            # Base64 문자열을 PostgreSQL BYTEA를 위한 bytes 객체로 변환
            update_data['face'] = base64.b64decode(face_base64)
        except Exception:
            raise HTTPException(
                status_code=400, 
                detail=error_response(error_code="INVALID_BASE64", message="제공된 얼굴 데이터가 유효한 Base64 형식이 아닙니다.")
            )
        
    success, error_details = update_student(sid, update_data)
    if not success:
        raise HTTPException(status_code=500, detail=error_details.get('error_code'))
        
    return success_response(message="USER_UPDATE_SUCCESS", status_code=201)

# --- 회원 정보 삭제 핸들러 (POST /user/delete) ---
# @router.post("/delete")
# async def delete_user_handler(data: Dict[str, Any]):
#     face_data = data.get('face')
    
#     # 1. 얼굴 데이터 필수값 확인 (400 방어)
#     if not validate_input(data, ['face']): 
#         raise HTTPException(status_code=400, detail="EMPTY_DATA")
    
#     # 2. 얼굴 데이터로 SID 찾기 및 인증 (404 방어)
#     result = get_student_ID_by_face(face_data)
#     if isinstance(result, tuple):
#         raise HTTPException(status_code=404, detail=result[1].get('error_code'))
    
#     sid_to_delete = result # 인증된 sid
    
#     # 3. 회원 기록 삭제 (4단계 DELETE 트랜잭션 - 500 방어)
#     if not execute_delete_students(sid_to_delete):
#         raise HTTPException(status_code=500, detail="DB_ERROR")
        
#     return success_response(message="USER_DELETE_SUCCESS", status_code=201)

import base64 # 사용하지 않더라도 기존 코드와의 일관성을 위해 유지

# ... (다른 import 유지)
# from core_service import check_student_exists, execute_delete_students
# from utils.helper_functions import validate_input, success_response

@router.post("/delete")
async def delete_user_handler(data: Dict[str, Any]):
    """
    회원 정보를 삭제합니다. (sid를 받아서 즉시 삭제)
    """
    
    # 1. sid 필수값 확인 (400 방어)
    # 🚨 수정: 'face' 대신 'sid'를 필수로 확인합니다.
    if not validate_input(data, ['sid']): 
        raise HTTPException(status_code=400, detail="EMPTY_DATA")
    
    sid_to_delete = data.get('sid')
    
    # 2. 삭제할 회원의 존재 여부 확인 (404 방어)
    # 🚨 추가: 삭제 전 해당 sid가 DB에 있는지 확인합니다.
    if not check_student_exists(sid_to_delete):
        raise HTTPException(
            status_code=404, 
            detail=error_response(error_code="USER_NOT_FOUND", message=f"학번 {sid_to_delete}는 등록되지 않은 회원입니다.")
        )
        
    # 3. 회원 기록 삭제 (DELETE 트랜잭션 실행 - 500 방어)
    # execute_delete_students는 True 또는 (False, 오류 상세) 튜플을 반환한다고 가정합니다.
    success, error_details = execute_delete_students(sid_to_delete)
    
    if not success:
        # DB 삭제 중 오류 발생 시 (500 Internal Server Error)
        raise HTTPException(
            status_code=500, 
            detail=error_response(
                error_code="DB_ERROR", 
                message=f"회원 정보 삭제 중 내부 데이터베이스 오류가 발생했습니다. 상세: {error_details.get('message', '알 수 없음')}"
            )
        )
        
    # 4. 성공 응답 반환 (201 Created)
    return success_response(message="USER_DELETE_SUCCESS", status_code=status.HTTP_201_CREATED)

# # --- 회원 정보 확인 핸들러 (GET /user/info) ---
# @router.get("/info")
# async def get_user_info_handler(sid: str = Query(..., description="조회할 회원의 학번 (SID)")):
    
#     # 1. 대상 회원 정보 조회 (SELECT)
#     user_data = get_user_info(sid) 
    
#     if user_data is None:
#         raise HTTPException(status_code=404, detail="NOT_FOUND")

#     # 2. 성공 응답 반환
#     return success_response(message="USER_INFO_SUCCESS", status_code=200, data=user_data)


@router.post("/exist", status_code=status.HTTP_201_CREATED)
async def register_user_handler(data: Dict[str, Any]):
    """
    새로운 학생 회원 정보를 등록합니다. (sid, name 필수, face 선택)
    """
    
    # 1. JSON 필수값 누락 확인 (400 Bad Request 방어)
    # 🚨 수정: sid와 name은 필수입니다. face 데이터는 선택입니다.
    REQUIRED_KEYS = ['sid', 'name']
    validation_result = validate_input(data, REQUIRED_KEYS)
    
    # name 또는 sid가 누락된 경우
    if validation_result is not True:
        _, error_detail = validation_result
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(
                error_code=error_detail['error_code'], 
                message=error_detail['message']
            )
        )
        
    # 🚨 추가: sid와 name은 필수지만, face 데이터가 완전히 없을 경우 DB 삽입 전 방어 로직
    # (선택적으로 face가 없더라도 등록은 가능하나, face가 있을 경우에만 변환)
    sid = data.get('sid')
    name = data.get('name') # 🚨 추가: name 데이터 추출
    
    # 2. face 데이터 처리
    # Postman에서 받은 Base64 문자열을 PostgreSQL BYTEA 타입을 위한 bytes 객체로 변환합니다.
    face_data = None
    face_data_base64 = data.get('face')
    
    if face_data_base64:
        try:
            face_data = base64.b64decode(face_data_base64)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response(
                    error_code="INVALID_BASE64",
                    message="제공된 얼굴 데이터(face)가 유효한 Base64 형식이 아닙니다."
                )
            )
            
    # 3. 회원 존재 중복 확인 (409 Conflict 방어)
    if check_student_exists(sid):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_response(
                error_code="ALREADY_EXIST_USER",
                message=f"학번 {sid}는 이미 등록된 회원입니다."
            )
        )

    # 4. 회원 기록 최종 저장 (INSERT 트랜잭션 실행)
    # 🚨 수정: execute_insert_student(sid, name, face_data) 형태로 호출 매개변수 변경
    success, error_details = execute_insert_student(sid, name, face_data)
    
    if not success:
        # DB 저장 중 오류 발생 시 (500 Internal Server Error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                error_code="DB_ERROR",
                message=f"회원 정보 등록 중 내부 데이터베이스 오류가 발생했습니다. 상세: {error_details.get('message', '알 수 없음')}"
            )
        )
        
    # 5. 성공 응답 반환 (201 Created)
    return success_response(
        message="USER_REGISTER_SUCCESS",
        status_code=status.HTTP_201_CREATED,
        data={"sid": sid, "name": name} # 생성된 리소스의 식별자를 포함하여 반환
    )

@router.post("/prev_exist")
async def check_existence_handler(data: Dict[str, Any]):
    """
    [API Handler] 이름과 학번이 DB에 이미 존재하는지(중복) 확인합니다.
    """
    REQUIRED_KEYS = ['sid', 'name']
    
    # 1. 필수값 검사 (유효성 검사는 프론트엔드에서 완료했다고 가정)
    if not validate_input(data, REQUIRED_KEYS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="EMPTY_DATA")
    
    sid = data.get('sid')
    name = data.get('name')
    
    # 2. DB 중복 확인 (core_service 호출)
    # 🚨 수정된 check_student_exists 함수 호출 (sid 또는 name이 중복인지 확인)
    # Note: check_student_exists가 True 또는 False를 반환하므로, 
    #       DB 연결 오류는 여기서는 False로 처리되고 409나 200으로 이어지게 됩니다.
    is_exist = prev_check_student(sid, name) 
    
    # 3. 응답 반환
    if is_exist:
        # 🚨 중복 발견 시 409 Conflict 반환
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_response(
                error_code="ALREADY_EXIST",
                message=f"학번({sid}) 또는 이름({name})이 이미 등록되어 있습니다."
            )
        )
    else:
        # 중복 없음 (등록 가능)
        return success_response(
            message="USER_AVAILABLE_FOR_ENROLLMENT",
            status_code=status.HTTP_200_OK,
            data={"sid": sid, "exists": False}
        )
