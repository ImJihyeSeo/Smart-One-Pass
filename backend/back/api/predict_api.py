# back/api/predict_api.py

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, List
from datetime import datetime
from ..services.predict_service import predict_library_seats

router = APIRouter(prefix="/predict", tags=["prediction"])

@router.post("/results", response_model=Dict[str, List[Dict[str, str]]])
async def get_prediction(payload: Dict = Body(...)):
    """
    프론트엔드 요청 예시: { "target_time": "2025-11-25 14:00:00" }
    """
    try:
        time_str = payload.get("target_time")
        if not time_str:
            raise HTTPException(status_code=400, detail="target_time is required")

        # 문자열 -> datetime 변환
        target_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        
        # 서비스 로직 호출
        results = predict_library_seats(target_dt)
        
        return {"results": results}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD HH:MM:SS")
    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))