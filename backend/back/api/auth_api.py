from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from ..services.core_service import check_student_exists, execute_delete_students, get_student_ID_by_face, check_access_of_student, execute_insert_student, update_student, process_access_record, create_reservation, check_time, get_access_records, get_seat_information, check_time_overlap, get_reservation_status, check_student_inside
from ..utils.helper_functions import error_response, success_response, format_db_rows_to_json, validate_input
# 🚨 상단에 base64 import 추가 (필수)
import base64
from fastapi import APIRouter, HTTPException, Query, status # status 추가

router = APIRouter()




# 2. 얼굴 데이터를 주고 등록된 회원인지 DB에서 확인

@router.post("/check")
async def check_access_handler(data: Dict[str, Any]):
    
    # 1. 값 추출 및 필수 입력값 확인 (DB X - Block 2)
    face_base64 = data.get('face')
    required_keys = ['face']
    
    if not validate_input(data, required_keys): 
        # face_data가 누락되었을 경우 400 Bad Request 발생 및 중단
        raise HTTPException(status_code=400, detail="EMPTY_DATA")
    
    # 🚨 1. Base64 디코딩 (PostgreSQL BYTEA 비교를 위한 bytes 변환)
    try:
        face_data = base64.b64decode(face_base64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(error_code="INVALID_BASE64", message="제공된 얼굴 데이터가 유효한 Base64 형식이 아닙니다.")
        )
    
    # 2. 얼굴 데이터가 일치하는 sid를 찾기 (SELECT - Block 10)
    # 이 함수는 sid(문자열)를 반환하거나, 못 찾거나 오류 시 (False, error_data)를 반환합니다.
    result = get_student_ID_by_face(face_data)
    
    if isinstance(result, tuple):
        # NOT_FOUND (얼굴 불일치) 또는 DB 오류 발생 시 404 반환
        error_details = result[1]
        
        # 🚨 NOT_FOUND가 아닌 DB_CONNECTION_ERROR 등 500 오류는 500으로 반환
        if error_details.get('error_code') in ["DB_CONNECTION_ERROR", "DB_EXECUTION_ERROR"]:
            raise HTTPException(status_code=500, detail=error_details.get('error_code'))
        
        raise HTTPException(status_code=404, detail=error_details.get('error_code'))

    sid_found = result # 인증에 성공한 sid (문자열)
    
    
    # 3. 성공 응답 반환
    # 200 OK와 함께 인증된 sid를 data 필드에 담아 반환합니다.
    return success_response(
        message="ACCESS_CHECK_SUCCESS", 
        status_code=200,
        # sid를 직접 담아 다음 API 호출에 사용할 수 있도록 제공합니다.
        data={"sid": sid_found} 
    )

