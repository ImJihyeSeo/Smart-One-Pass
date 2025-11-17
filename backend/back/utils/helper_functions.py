from typing import List, Dict, Any, Optional, Tuple, Union

# Note: sqlite3.Row 타입을 사용하기 위해 sqlite3 모듈을 import합니다.

# --- 1. 공통 오류 응답 포장 (error_response) ---
def error_response(
    error_code: str, 
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    HTTPException의 detail에 사용될 표준 오류 응답 딕셔너리를 포장하여 반환합니다.
    (모든 실패 응답은 success: False를 기본으로 합니다.)
    """
    
    # 메시지가 제공되지 않았을 경우, 오류 코드 자체를 메시지로 사용합니다.
    if message is None:
        message = error_code
        
    # 당신이 설계한 공통 JSON 실패 구조에 맞춰 딕셔너리를 구성합니다.
    response_body = {
        "success": False,
        "message": message,
        "error_code": error_code
    }
    
    # 이 딕셔너리는 FastAPI의 HTTPException(detail=...)에 들어갑니다.
    return response_body

# --- 2. 성공 응답 포장 (success_response) ---

# success_response 함수의 매개변수와 반환값 정의
# 반환값: Tuple[JSONResponse, int] 형태로 HTTP 응답 데이터와 상태 코드를 반환합니다.
def success_response(
    message: str, 
    status_code: int, 
    data: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], int]:
    
    # 1. JSON 본문(Body)의 기본 구조를 만듭니다.
    response_body = {
        "success": True,
        "message": message,
        # 성공 시 error_code는 필요 없습니다.
    }
    
    # 2. 'data'가 있다면 JSON 본문에 추가합니다. (선택적 매개변수 처리)
    if data is not None:
        # data는 단일 객체일 수도 있고, 목록(List)일 수도 있습니다.
        # FastAPI는 딕셔너리를 자동으로 JSON으로 변환합니다.
        response_body["data"] = data
        
    # 3. 최종 포장된 JSON 본문(딕셔너리)과 HTTP 상태 코드를 튜플로 반환합니다.
    # 이 튜플은 FastAPI 핸들러의 'return' 문에서 사용됩니다.
    return response_body, status_code

# --- 3. DB Row 객체를 JSON 리스트로 번역 (format_db_rows_to_json) ---
def format_db_rows_to_json(
    db_rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    SQLite의 Row 객체 리스트를 파이썬의 딕셔너리 리스트 (최종 JSON 형태)로 변환합니다.
    """
    
    # 1. DB 결과가 None이거나 비어있으면 빈 리스트 []를 반환하여 안전하게 처리합니다.
    if not db_rows:
        return []
    
    # json_list = []
    # 2. psycopg2의 RealDictRow 객체를 순수 dict로 변환
    # (FastAPI가 RealDictRow도 잘 처리하지만, dict로 명시적 변환하는 것이 안전합니다.)
    json_list = [dict(row) for row in db_rows]
    
    # 2. 각 행(Row)을 반복하며 dict() 함수로 딕셔너리 리스트를 만듭니다.
    # for row in db_rows:
    #     # sqlite3.Row 객체는 dict()으로 변환되어야 클라이언트가 원하는 JSON 형태가 됩니다.
    #     json_list.append(row)
        
    # json_list = [row for row in db_rows]
    
    return json_list

# JSON 필수값 누락 확인

# --- JSON 필수값 누락 확인 (validate_input) ---

def validate_input(
    data: Dict[str, Any], 
    required_key_list: List[str]
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    입력된 딕셔너리(JSON 본문)에 required_key_list에 지정된 모든 필수 키가 
    포함되어 있는지 확인합니다.

    Args:
        data: API 요청 본문에서 받은 딕셔너리 데이터.
        required_key_list: 필수적으로 포함되어야 하는 키 이름의 리스트.

    Returns:
        True (모든 필수값 존재) 또는 (False, 오류 상세 정보 딕셔너리).
    """
    
    missing_keys = []
    
    # 1. required_key_list를 순회하며 data에 키가 있는지 확인
    for key in required_key_list:
        # 키가 data에 없거나, 키는 있지만 값이 None인 경우 (필수값이므로 빈 값은 허용 안 함)
        # Note: 'key in data'는 키가 있는지 확인하고, 'data.get(key)'는 값이 None인지 확인합니다.
        if key not in data or data.get(key) is None: 
            missing_keys.append(key)
            
    # 2. 누락된 키가 있는지 확인하여 결과 반환
    if missing_keys:
        # 누락된 키가 하나라도 있다면 오류 정보와 함께 False 반환
        error_message = f"다음 필수 필드가 누락되었거나 값이 비어있습니다: {', '.join(missing_keys)}"
        
        # 🚨 이 함수는 오류 응답 포장 함수(error_response)와 별개로 순수한 오류 튜플을 반환합니다.
        return False, {
            "error_code": "MISSING_REQUIRED_FIELDS", 
            "message": error_message
        }
    else:
        # 모든 필수 필드가 존재함
        return True