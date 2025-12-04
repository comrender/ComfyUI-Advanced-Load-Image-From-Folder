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
        if not image_folder or not image_folder.strip():
            raise ValueError("Image folder path is empty!")
        image_folder = image_folder.strip()
        if not os.path.isdir(image_folder):
            raise ValueError(f"Folder does not exist: {image_folder}")

        supported_exts = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif'}
        files = [
            f for f in os.listdir(image_folder)
            if os.path.splitext(f)[1].lower() in supported_exts
            and os.path.isfile(os.path.join(image_folder, f))
        ]

        if not files:
            raise ValueError(f"No supported images found in: {image_folder}")

        files.sort(key=lambda x: x.lower())
        if index >= len(files):
            index = index % len(files) if files else 0

        selected_file = files[index]
        file_path = os.path.join(image_folder, selected_file)

        # === Load image (animated GIF/TIFF support) ===
        img = Image.open(file_path)
        img = ImageOps.exif_transpose(img)

        frames = []
        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("RGB")
            arr = np.array(frame).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr)[None, ...]
            frames.append(tensor)

        image_out = torch.cat(frames, dim=0) if len(frames) > 1 else frames[0]

        # === Extract metadata ===
        metadata = {}
        try:
            # PNG text chunks (including Windows XP tags)
            if file_path.lower().endswith('.png') and hasattr(img, 'text'):
                for key, value in img.text.items():
                    metadata[key] = value

            # EXIF (JPEG/TIFF)
            exif = img.getexif()
            if exif is not None:
                for tag_id, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    metadata[tag_name] = value

                # GPS and other IFDs
                for ifd_id, ifd_name in ExifTags.IFD.items():
                    ifd = exif.get_ifd(ifd_id)
                    if ifd:
                        decoded = {ExifTags.GPSTAGS.get(k, k): v for k, v in ifd.items()}
                        metadata[ifd_name] = decoded

        except Exception as e:
            print(f"[AdvancedLoadImageFromFolder] Metadata warning: {e}")

        # === Fix Windows XP strings (they are UTF-16 little-endian with null terminator) ===
        xp_keys = ["XPTitle", "XPComment", "XPAuthor", "XPKeywords", "XPSubject"]
        for key in xp_keys:
            if key in metadata and isinstance(metadata[key], bytes):
                try:
                    # Remove trailing nulls and decode as UTF-16LE
                    clean_bytes = metadata[key].rstrip(b'\x00')
                    metadata[key] = clean_bytes.decode('utf-16-le')
                except:
                    metadata[key] = f"<failed to decode {key}>"

        # === Safe JSON serialization ===
        def make_serializable(obj):
            if isinstance(obj, bytes):
                try:
                    return obj.decode('utf-8', errors='replace')
                except:
                    return f"<binary: {len(obj)} bytes>"
            elif isinstance(obj, (list, tuple)):
                return [make_serializable(i) for i in obj]
            elif isinstance(obj, dict):
                return {str(k): make_serializable(v) for k, v in obj.items()}
            else:
                return obj

        safe_metadata = make_serializable(metadata)
        metadata_str = json.dumps(safe_metadata, indent=2, ensure_ascii=False, default=str)

        # === Return filename WITHOUT extension ===
        name_without_ext = os.path.splitext(selected_file)[0]

        return (image_out, name_without_ext, metadata_str)

    @classmethod
    def IS_CHANGED(cls, image_folder: str, index: int):
        if not image_folder or not os.path.isdir(image_folder):
            return "invalid_folder"
        try:
            files = [f for f in os.listdir(image_folder) if os.path.isfile(os.path.join(image_folder, f))]
            files.sort(key=str.lower)
            name_hash = hashlib.md5(''.join(files).encode('utf-8', errors='ignore')).hexdigest()
            latest_mtime = max((os.path.getmtime(os.path.join(image_folder, f)) for f in files), default=0)
            return f"{name_hash}_{latest_mtime}_{index}"
        except:
            return "error_scanning_folder"


NODE_CLASS_MAPPINGS = {
    "Advanced Load Image From Folder": AdvancedLoadImageFromFolder
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Advanced Load Image From Folder": "Advanced Load Image From Folder"
}
