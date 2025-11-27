import os
import json
import hashlib
from PIL import Image, ImageOps, ImageSequence, ExifTags
import torch
import numpy as np
import folder_paths

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

        # Supported extensions (add more if needed)
        supported_exts = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif'}
        files = [
            f for f in os.listdir(image_folder)
            if os.path.splitext(f)[1].lower() in supported_exts
        ]

        if not files:
            raise ValueError(f"No supported images found in folder: {image_folder}")

        # Critical: Sort case-insensitively → consistent order on Windows AND Linux
        files.sort(key=lambda x: x.lower())

        if index >= len(files):
            raise ValueError(f"Index {index} out of range. Only {len(files)} image(s) found.")

        selected_file = files[index]
        file_path = os.path.join(image_folder, selected_file)

        img = Image.open(file_path)
        img = ImageOps.exif_transpose(img)  # Fix orientation

        # Handle animated GIFs / multi-page TIFFs
        frames = []
        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("RGB")
            if frame.mode == 'I':
                frame = frame.point(lambda i: i * (1 / 255.0))
            arr = np.array(frame).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr).unsqueeze(0)  # [1, H, W, 3]
            frames.append(tensor)

        image_out = torch.cat(frames, dim=0) if len(frames) > 1 else frames[0]

        # Extract metadata
        metadata = {}
        try:
            if file_path.lower().endswith('.png'):
                if hasattr(img, 'info'):
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
            print(f"[AdvancedLoadImageFromFolder] Warning: Could not read metadata: {e}")

        metadata_str = json.dumps(metadata, indent=2, ensure_ascii=False)

        return (image_out, selected_file, metadata_str)

    @classmethod
    def IS_CHANGED(cls, image_folder, index):
        # Invalidate cache if folder contents change
        if not os.path.isdir(image_folder):
            return "invalid_folder"
        try:
            files = os.listdir(image_folder)
            mtime = max(os.path.getmtime(os.path.join(image_folder, f)) for f in files)
            return f"{hashlib.md5(''.join(sorted(files)).encode()).hexdigest()}_{mtime}_{index}"
        except:
            return "error"


# ─────────────────────────────────────────────────────────────────────────────
# Node registration (required!)
# ─────────────────────────────────────────────────────────────────────────────
NODE_CLASS_MAPPINGS = {
    "Advanced Load Image From Folder": AdvancedLoadImageFromFolder
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Advanced Load Image From Folder": "Advanced Load Image From Folder"
}

# Optional: expose for web extensions / search
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
