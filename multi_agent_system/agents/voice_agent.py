import json
from tools.voice_tool import VoiceTool

class VoiceAgent:
    def __init__(self):
        self.tool = VoiceTool()

    def run(self, audio_file_path: str = None, child_id: str = "unknown", text_input: str = None) -> dict:
        result_str = self.tool._run(audio_file_path=audio_file_path, child_id=child_id, text_input=text_input)
        result = json.loads(result_str)
        if result["success"]:
            return result["data"]
        return {"transcript": "", "analysis": f"Voice analysis failed: {result.get('error')}"}
