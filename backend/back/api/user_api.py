# api/user_api.py (회원 정보 수정 및 삭제, 조회)
from fastapi import APIRouter, HTTPException, status, Query
from typing import Dict, Any, Optional, List

# from database import get_db_connection, initialize_db
from ..services.core_service import check_student_exists, execute_delete_students, get_student_ID_by_face, check_access_of_student, execute_insert_student, update_student, process_access_record, create_reservation, check_time, get_access_records, get_seat_information, check_time_overlap, get_reservation_status, check_student_inside, prev_check_student
from ..utils.helper_functions import error_response, success_response, format_db_rows_to_json, validate_input
# services 및 utils 폴더에서 필요한 함수들을 모두 import 가정

import numpy as np
from pydantic import BaseModel


router = APIRouter()


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
    


# ==========================================
# 1. 데이터 모델 (클라이언트가 보낼 데이터 양식)
# ==========================================

# /enroll/sample 요청 받을 때 쓸 양식
class EnrollSampleRequest(BaseModel):
    sid: str              # 학번
    embedding: List[float] # 얼굴 벡터 (숫자 512개 리스트)

# /enroll/finish 요청 받을 때 쓸 양식
class EnrollFinishRequest(BaseModel):
    sid: str              # 학번
    name: str             # 이름

# ==========================================
# 2. 가짜 DB (실제로는 PostgreSQL/MySQL 사용 권장)
# ==========================================

# (1) 임시 보관함: 샘플들을 잠시 모아두는 곳
# 구조: { "20231234": [[0.1, 0.2...], [0.3, 0.4...]] }
enrollment_sessions: Dict[str, List[List[float]]] = {}



# [API 1] 샘플 수집 (accumulate_sample 대응)
@router.post("/enroll/sample")
async def enroll_sample_handler(data: EnrollSampleRequest):
    """
    클라이언트로부터 얼굴 벡터 샘플을 받아 서버 메모리에 임시 저장합니다.
    """
    sid = data.sid
    vector = data.embedding

    # 1. 해당 학번의 세션이 없으면 생성
    if sid not in enrollment_sessions:
        enrollment_sessions[sid] = []
    
    # 2. 벡터 리스트에 추가
    enrollment_sessions[sid].append(vector)
    
    count = len(enrollment_sessions[sid])
    print(f"📸 [Enroll] {sid}: 샘플 {count}개 확보")
    
    return success_response(
        message="SAMPLE_COLLECTED",
        status_code=200,
        data={"count": count}
    )

# [API 2] 등록 완료 (finish_enrollment 대응)
@router.post("/enroll/finish")
async def enroll_finish_handler(data: EnrollFinishRequest):
    """
    모인 샘플들의 평균을 계산하여 '최종 얼굴 데이터'를 만든 뒤,
    DB의 students 테이블에 저장(INSERT 또는 UPDATE)합니다.
    """
    sid = data.sid
    name = data.name

    # 1. 저장된 샘플이 있는지 확인
    if sid not in enrollment_sessions or not enrollment_sessions[sid]:
        raise HTTPException(
            status_code=400, 
            detail=error_response("NO_SAMPLES", "수집된 얼굴 샘플이 없습니다.")
        )

    try:
        # 2. [핵심 로직] 평균 벡터 계산 (Numpy 사용)
        vectors = np.array(enrollment_sessions[sid], dtype=np.float32)
        mean_vector = np.mean(vectors, axis=0)
        
        # 3. 정규화 (L2 Norm) - 얼굴 인식 정확도를 위해 필수
        norm = np.linalg.norm(mean_vector)
        if norm > 0:
            mean_vector = mean_vector / norm
            
        # 4. 바이트 변환 (PostgreSQL BYTEA 타입에 저장하기 위함)
        # float32 배열을 bytes로 직렬화합니다.
        final_face_bytes = mean_vector.tobytes()

        # 5. DB 저장 (이미 회원이 있으면 Update, 없으면 Insert)
        if check_student_exists(sid):
            # 기존 회원이면 얼굴 정보만 업데이트
            success, err = update_student(sid, {"face": final_face_bytes})
        else:
            # 신규 회원이면 새로 등록
            success, err = execute_insert_student(sid, name, final_face_bytes)

        if not success:
            raise HTTPException(status_code=500, detail=err)

        # 6. 메모리 정리 (세션 삭제)
        del enrollment_sessions[sid]
        
        return success_response(
            message="ENROLLMENT_FINISHED",
            status_code=200,
            data={"sid": sid, "name": name}
        )

    except Exception as e:
        print(f"Enrollment Finish Error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=error_response("SERVER_ERROR", str(e))
        )