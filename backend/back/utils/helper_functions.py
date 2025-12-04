from typing import List, Dict, Any, Optional, Tuple, Union
from fastapi.responses import JSONResponse
from datetime import date, datetime, time

# 1. 공통 오류 응답 포장
def error_response(
    error_code: str, 
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    HTTPException의 detail에 사용될 표준 오류 응답 딕셔너리를 포장하여 반환합니다.
    (모든 실패 응답은 success: False를 기본으로 합니다.)
    """
    
    if message is None:
        message = error_code
        
    response_body = {
        "success": False,
        "message": message,
        "error_code": error_code
    }
    
    return response_body


# 2. 성공 응답 포장
def success_response(
    message: str, 
    status_code: int, 
    data: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    
    response_body = {
        "success": True,
        "message": message,
    }
    
    if data is not None:
        response_body["data"] = data
        
    return JSONResponse(content=response_body, status_code=status_code)

# 3. DB Row 객체를 JSON 리스트로
def format_db_rows_to_json(
    db_rows: List[Any]
) -> List[Dict[str, Any]]:
    """
    DB 조회 결과(Row 객체 리스트)를 일반 딕셔너리 리스트로 변환합니다.
    # """
    json_list = []
    
    if not db_rows:
        return []

    for row in db_rows:
        row_dict = dict(row)
        
        for key, value in row_dict.items():
            if isinstance(value, (date, datetime)):
                row_dict[key] = str(value) 
            
            elif isinstance(value, time):
                row_dict[key] = str(value) 
                
        json_list.append(row_dict)
        
    return json_list


# 4. JSON 필수값 누락 확인
def validate_input(
    data: Dict[str, Any], 
    required_key_list: List[str]
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    입력된 딕셔너리(JSON 본문)에 required_key_list에 지정된 모든 필수 키가 
    포함되어 있는지 확인합니다.
    """
    
    missing_keys = []
    
    for key in required_key_list:
        if key not in data or data.get(key) is None: 
            missing_keys.append(key)
            
    if missing_keys:
        error_message = f"다음 필수 필드가 누락되었거나 값이 비어있습니다: {', '.join(missing_keys)}"
        
        return False, {
            "error_code": "MISSING_REQUIRED_FIELDS", 
            "message": error_message
        }
    else:
        return True