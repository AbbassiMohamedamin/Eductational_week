import argparse
import json
import os
from pathlib import Path

import httpx

from tools.vision_tool import VisionTool


def ensure_test_image(image_path: str | None) -> str:
    if image_path:
        return image_path

    target = Path("temp_uploads") / "vlm_probe_sample.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        return str(target)

    sample_url = "https://images.unsplash.com/photo-1518779578993-ec3579fee39f?auto=format&fit=crop&w=1200&q=80"
    with httpx.Client(timeout=30.0) as client:
        response = client.get(sample_url)
        response.raise_for_status()
        target.write_bytes(response.content)

    return str(target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run VisionTool on a local image and print the full VLM response.")
    parser.add_argument("--image", help="Path to local image. If omitted, a sample image is downloaded.")
    args = parser.parse_args()

    image_path = ensure_test_image(args.image)
    print(f"Using image: {image_path}")

    tool = VisionTool()
    result = tool.execute(image_path=image_path)

    print("\n=== Raw AgentToolResult ===")
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))

    if result.success:
        data = result.data or {}
        print("\n=== VLM Output Summary ===")
        print("components_detected:", data.get("components_detected"))
        print("has_fault:", data.get("has_fault"))
        print("fault_description:", data.get("fault_description"))
        print("arabic_explanation:", data.get("arabic_explanation"))
        print("arabic_correction:", data.get("arabic_correction"))


if __name__ == "__main__":
    main()
