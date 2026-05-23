import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import io

from srt_processor.processor import process_subtitles
from srt_processor.srt_parser import parse_srt
from srt_processor.text_matcher import align_subtitles
from srt_processor.ai_corrector import ai_correct_entries

app = FastAPI(
    title="字幕校对 API",
    description="字幕文件智能校对与修正 API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/proofread")
async def proofread_subtitles(
    original_srt: UploadFile = File(..., description="原字幕文件 (.srt)"),
    recognized_srt: UploadFile = File(..., description="识别字幕文件 (.srt)")
):
    if not original_srt.filename.endswith('.srt'):
        raise HTTPException(status_code=400, detail="原字幕必须是 .srt 格式")

    if not recognized_srt.filename.endswith('.srt'):
        raise HTTPException(status_code=400, detail="识别字幕必须是 .srt 格式")

    try:
        original_content = await original_srt.read()
        original_text = original_content.decode('utf-8')

        recognized_content = await recognized_srt.read()
        recognized_text = recognized_content.decode('utf-8')

        if not original_text.strip():
            raise HTTPException(status_code=400, detail="原字幕文件为空")

        if not recognized_text.strip():
            raise HTTPException(status_code=400, detail="识别字幕文件为空")

        result = process_subtitles(original_text, recognized_text)

        return JSONResponse(content={
            "success": True,
            "data": {
                "corrected_srt": result['corrected_srt'],
                "timeline": result['timeline'],
                "stats": result['stats'],
            }
        })

    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码错误，请使用 UTF-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理错误: {str(e)}")


@app.post("/api/v1/proofread/ai")
async def proofread_subtitles_ai(
    original_srt: UploadFile = File(..., description="原字幕文件 (.srt)"),
    recognized_srt: UploadFile = File(..., description="识别字幕文件 (.srt)")
):
    if not original_srt.filename.endswith('.srt'):
        raise HTTPException(status_code=400, detail="原字幕必须是 .srt 格式")

    if not recognized_srt.filename.endswith('.srt'):
        raise HTTPException(status_code=400, detail="识别字幕必须是 .srt 格式")

    try:
        original_content = await original_srt.read()
        original_text = original_content.decode('utf-8')

        recognized_content = await recognized_srt.read()
        recognized_text = recognized_content.decode('utf-8')

        if not original_text.strip():
            raise HTTPException(status_code=400, detail="原字幕文件为空")

        if not recognized_text.strip():
            raise HTTPException(status_code=400, detail="识别字幕文件为空")

        original_entries = parse_srt(original_text, is_original=True)
        recognized_entries = parse_srt(recognized_text, is_original=False)

        recognized_data = []
        for entry in recognized_entries:
            recognized_data.append({
                'index': entry.index,
                'start_time': entry.start_time,
                'end_time': entry.end_time,
                'text': entry.english or entry.text
            })

        original_data = []
        for entry in original_entries:
            original_data.append({
                'index': entry.index,
                'start_time': entry.start_time,
                'end_time': entry.end_time,
                'text': entry.text,
                'english': entry.english,
                'chinese': entry.chinese
            })

        aligned_entries = align_subtitles(recognized_data, original_data)

        ai_result = await ai_correct_entries(recognized_data, original_data, aligned_entries)

        from srt_processor.srt_parser import SRTEntry, format_srt
        from srt_processor.text_corrector import capitalize_text
        corrected_srt_entries = []
        matched_org_idx = set()

        for aligned in aligned_entries:
            if aligned.get('matched_original_index'):
                matched_org_idx.add(aligned['matched_original_index'])

            timeline_entry = next(
                (t for t in ai_result['timeline']
                 if t['entry_index'] == aligned['index'] and t['status'] not in ('missing',)),
                None
            )

            if timeline_entry:
                final_text = timeline_entry['corrected_text']
            else:
                final_text = capitalize_text(aligned.get('text', ''))

            corrected_srt_entries.append(SRTEntry(
                index=aligned['index'],
                start_time=aligned['start_time'],
                end_time=aligned['end_time'],
                text=final_text,
                english=final_text
            ))

        corrected_srt = format_srt(corrected_srt_entries)

        return JSONResponse(content={
            "success": True,
            "data": {
                "corrected_srt": corrected_srt,
                "timeline": ai_result['timeline'],
                "stats": ai_result['stats'],
            }
        })

    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码错误，请使用 UTF-8")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 校对错误: {str(e)}")


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "message": "字幕校对 API 运行中"}


frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
