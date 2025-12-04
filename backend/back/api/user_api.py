from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, List
from ..services.core_service import check_student_exists, execute_delete_students, execute_insert_student, update_student, prev_check_student
from ..utils.helper_functions import error_response, success_response, validate_input
import numpy as np
from pydantic import BaseModel
import base64


router = APIRouter()

# 1. 학생 등록
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user_handler(data: Dict[str, Any]):
    """
    새로운 학생 회원 정보를 등록합니다. (sid, name 필수, face 선택)
    """
    
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
        
    sid = data.get('sid')
    name = data.get('name')
    
    # face 데이터 처리
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
            
    # 회원 존재 중복 확인
    if check_student_exists(sid):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_response(
                error_code="ALREADY_EXIST_USER",
                message=f"학번 {sid}는 이미 등록된 회원입니다."
            )
        )

    # 회원 기록 최종 저장
    success, error_details = execute_insert_student(sid, name, face_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                error_code="DB_ERROR",
                message=f"회원 정보 등록 중 내부 데이터베이스 오류가 발생했습니다. 상세: {error_details.get('message', '알 수 없음')}"
            )
        )
        
    return success_response(
        message="USER_REGISTER_SUCCESS",
        status_code=status.HTTP_201_CREATED,
        data={"sid": sid, "name": name}
    )

# 2. 회원 정보 수정
@router.post("/update")
async def update_user_handler(data: Dict[str, Any]):
    sid = data.get('sid')
    
    required_id = ['sid']
    if not validate_input(data, required_id) or (not data.get('face') and not data.get('card')):
        raise HTTPException(status_code=400, detail="EMPTY_DATA")
        
    if not check_student_exists(sid):
        raise HTTPException(status_code=404, detail="NOT_FOUND")

    update_data = {}
    
    if 'face' in data:
        face_base64 = data['face']
        try:
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


# 3. 회원 정보 삭제
@router.post("/delete")
async def delete_user_handler(data: Dict[str, Any]):
    """
    회원 정보를 삭제합니다. (sid를 받아서 즉시 삭제)
    """
    
    if not validate_input(data, ['sid']): 
        raise HTTPException(status_code=400, detail="EMPTY_DATA")
    
    sid_to_delete = data.get('sid')
    
    if not check_student_exists(sid_to_delete):
        raise HTTPException(
            status_code=404, 
            detail=error_response(error_code="USER_NOT_FOUND", message=f"학번 {sid_to_delete}는 등록되지 않은 회원입니다.")
        )
        
    success, error_details = execute_delete_students(sid_to_delete)
    
    if not success:
        raise HTTPException(
            status_code=500, 
            detail=error_response(
                error_code="DB_ERROR", 
                message=f"회원 정보 삭제 중 내부 데이터베이스 오류가 발생했습니다. 상세: {error_details.get('message', '알 수 없음')}"
            )
        )
        
    return success_response(message="USER_DELETE_SUCCESS", status_code=status.HTTP_201_CREATED)


# 4. 학생 정보 존재 여부 확인
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
    


# 5. 얼굴 임베딩 데이터 등록

class EnrollSampleRequest(BaseModel):
    sid: str              
    embedding: List[float] 

class EnrollFinishRequest(BaseModel):
    sid: str              
    name: str          

enrollment_sessions: Dict[str, List[List[float]]] = {}



# 샘플 수집
@router.post("/enroll/sample")
async def enroll_sample_handler(data: EnrollSampleRequest):
    """
    클라이언트로부터 얼굴 벡터 샘플을 받아 서버 메모리에 임시 저장합니다.
    """
    sid = data.sid
    vector = data.embedding

    # 해당 학번의 세션이 없으면 생성
    if sid not in enrollment_sessions:
        enrollment_sessions[sid] = []
    
    # 벡터 리스트에 추가
    enrollment_sessions[sid].append(vector)
    
    count = len(enrollment_sessions[sid])
    print(f"[Enroll] {sid}: 샘플 {count}개 확보")
    
    return success_response(
        message="SAMPLE_COLLECTED",
        status_code=200,
        data={"count": count}
    )


# 등록 완료 
@router.post("/enroll/finish")
async def enroll_finish_handler(data: EnrollFinishRequest):
    """
    모인 샘플들의 평균을 계산하여 '최종 얼굴 데이터'를 만든 뒤,
    DB의 students 테이블에 저장(INSERT 또는 UPDATE)합니다.
    """
    sid = data.sid
    name = data.name

    # 저장된 샘플이 있는지 확인
    if sid not in enrollment_sessions or not enrollment_sessions[sid]:
        raise HTTPException(
            status_code=400, 
            detail=error_response("NO_SAMPLES", "수집된 얼굴 샘플이 없습니다.")
        )

    try:
        # 평균 벡터 계산
        vectors = np.array(enrollment_sessions[sid], dtype=np.float32)
        mean_vector = np.mean(vectors, axis=0)
        
        # 정규화 - 얼굴 인식 정확도를 위해 필수
        norm = np.linalg.norm(mean_vector)
        if norm > 0:
            mean_vector = mean_vector / norm
            
        # 바이트 변환 
        final_face_bytes = mean_vector.tobytes()

        # DB 저장
        if check_student_exists(sid):
            success, err = update_student(sid, {"face": final_face_bytes})
        else:
            success, err = execute_insert_student(sid, name, final_face_bytes)

        if not success:
            raise HTTPException(status_code=500, detail=err)

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