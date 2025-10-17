# # app/notify.py
# import httpx
# import os
# from dotenv import load_dotenv

# load_dotenv()

# def notify_evaluation_server(evaluation_url: str, payload: dict) -> bool:
#     """
#     Send repo details back to the evaluation server.
#     Retries with exponential backoff if needed.
#     """
#     headers = {"Content-Type": "application/json"}

#     delay = 1  # start with 1 second
#     for attempt in range(5):  # try up to 5 times
#         try:
#             r = httpx.post(evaluation_url, headers=headers, json=payload)
#             if r.status_code == 200:
#                 print("✅ Evaluation server notified successfully.")
#                 return True
#             else:
#                 print(f"⚠️ Attempt {attempt+1}: Server responded {r.status_code} - {r.text}")
#         except Exception as e:
#             print(f"❌ Attempt {attempt+1} failed: {e}")

#         # Exponential backoff
#         import time
#         time.sleep(delay)
#         delay *= 2

#     print("❌ Failed to notify evaluation server after retries.")
#     return False

# app/notify.py
import httpx
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def notify_evaluation_server(evaluation_url: str, payload: dict, request_timestamp: str = None) -> dict:
    """
    Send repo details back to the evaluation server with exponential backoff retry.
    
    Args:
        evaluation_url: The URL to POST to
        payload: The JSON payload to send
        request_timestamp: ISO format timestamp of original request (for 10-min deadline check)
    
    Returns:
        {
            "success": bool,
            "attempts": int,
            "total_time": float,
            "status_code": int,
            "error": str or None,
            "timestamp": datetime
        }
    """
    
    headers = {"Content-Type": "application/json"}
    
    # Check 10-minute deadline
    if request_timestamp:
        try:
            req_time = datetime.fromisoformat(request_timestamp)
            deadline = req_time + timedelta(minutes=10)
            if datetime.now() > deadline:
                return {
                    "success": False,
                    "attempts": 0,
                    "total_time": 0,
                    "status_code": 408,
                    "error": "Request exceeded 10-minute deadline",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            print(f"⚠️ Could not validate timestamp: {e}")
    
    # Exponential backoff: 1, 2, 4, 8, 16 seconds (max 5 attempts)
    delays = [1, 2, 4, 8, 16]
    start_time = time.time()
    last_status = None
    last_error = None
    
    for attempt in range(len(delays)):
        try:
            print(f"📤 Notification attempt {attempt + 1}/{len(delays)} to {evaluation_url}")
            
            r = httpx.post(
                evaluation_url,
                headers=headers,
                json=payload,
                timeout=10.0
            )
            
            last_status = r.status_code
            
            if r.status_code == 200:
                elapsed = time.time() - start_time
                print(f"✅ Evaluation server notified successfully (attempt {attempt + 1}).")
                return {
                    "success": True,
                    "attempts": attempt + 1,
                    "total_time": elapsed,
                    "status_code": 200,
                    "error": None,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                last_error = f"HTTP {r.status_code}: {r.text[:200]}"
                print(f"⚠️ Attempt {attempt + 1}: Server responded {r.status_code}")
                print(f"   Response: {r.text[:100]}")
        
        except httpx.TimeoutException as e:
            last_error = f"Timeout: {str(e)}"
            print(f"❌ Attempt {attempt + 1} timeout: {e}")
        
        except httpx.ConnectError as e:
            last_error = f"Connection error: {str(e)}"
            print(f"❌ Attempt {attempt + 1} connection error: {e}")
        
        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            print(f"❌ Attempt {attempt + 1} failed: {e}")
        
        # Sleep before retry (except on last attempt)
        if attempt < len(delays) - 1:
            delay = delays[attempt]
            print(f"⏳ Waiting {delay}s before retry...")
            time.sleep(delay)
    
    elapsed = time.time() - start_time
    print(f"❌ Failed to notify evaluation server after {len(delays)} attempts ({elapsed:.1f}s total).")
    
    return {
        "success": False,
        "attempts": len(delays),
        "total_time": elapsed,
        "status_code": last_status,
        "error": last_error,
        "timestamp": datetime.now().isoformat()
    }


def log_notification_result(task_id: str, result: dict, round_num: int = 1) -> None:
    """Log notification result for debugging."""
    
    log_entry = f"""
Notification Log - {datetime.now().isoformat()}
Task: {task_id} (Round {round_num})
Success: {result['success']}
Attempts: {result['attempts']}
Total Time: {result['total_time']:.2f}s
Status Code: {result['status_code']}
Error: {result['error'] or 'None'}
"""
    
    print(log_entry)
    
    # Optionally save to file
    log_file = f"/tmp/notifications_{task_id}.log"
    try:
        with open(log_file, "a") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"⚠️ Could not write to log file: {e}")
