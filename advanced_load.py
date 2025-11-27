import os
import json
import hashlib
from PIL import Image, ImageOps, ImageSequence, ExifTags
import torch
import numpy as np

class AdvancedLoadImageFromFolder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_folder": ("STRING", {"default": "", "multiline": False}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image", "file_name", "metadata")
    FUNCTION = "load_image"
    CATEGORY = "image/advanced"

    def load_image(self, image_folder: str, index: int):
        if not image_folder or not os.path.isdir(image_folder):
            raise ValueError(f"Invalid or missing folder: {image_folder}")

        supported_exts = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif'}
        files = [
            f for f in os.listdir(image_folder)
            if os.path.splitext(f)[1].lower() in supported_exts
        ]

        if not files:
            raise ValueError(f"No supported images found in: {image_folder}")

        # This line fixes your original Linux/Windows sorting issue
        files.sort(key=lambda x: x.lower())

        if index >= len(files):
            index = index % len(files)  # optional: wrap around instead of error
            # raise ValueError(f"Index {index} out of range ({len(files)} images)")

        selected_file = files[index]
        file_path = os.path.join(image_folder, selected_file)

        img = Image.open(file_path)
        img = ImageOps.exif_transpose(img)

        # Support animated GIFs / multi-page TIFFs
        frames = []
        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("RGB")
            arr = np.array(frame).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr).unsqueeze(0)
            frames.append(tensor)

        image_out = torch.cat(frames, dim=0) if len(frames) > 1 else frames[0]

        # Metadata extraction
        metadata = {}
        try:
            if file_path.lower().endswith('.png') and hasattr(img, 'info'):
                metadata = img.info
            else:
                exif = img.getexif()
                if exif:
                    metadata = {
                        ExifTags.TAGS.get(tag, tag): value
                        for tag, value in exif.items()
                        if tag in ExifTags.TAGS
                    }
        except Exception as e:
            print(f"[AdvancedLoadImageFromFolder] Metadata warning: {e}")

        metadata_str = json.dumps(metadata, indent=2, ensure_ascii=False)

        return (image_out, selected_file, metadata_str)

    @classmethod
    def IS_CHANGED(cls, image_folder, index):
        if not os.path.isdir(image_folder):
            return "invalid"
        try:
            files = sorted(os.listdir(image_folder))
            mtime = max(os.path.getmtime(os.path.join(image_folder, f)) for f in files)
            return f"{hashlib.md5(''.join(files).encode()).hexdigest()}_{mtime}_{index}"
        except:
            return "error"


# ────── Required for ComfyUI to detect the node ──────
NODE_CLASS_MAPPINGS = {
    "Advanced Load Image From Folder": AdvancedLoadImageFromFolder
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Advanced Load Image From Folder": "Advanced Load Image From Folder"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
