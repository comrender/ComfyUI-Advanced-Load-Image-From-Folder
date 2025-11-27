import os
import json
from PIL import Image, ImageOps, ImageSequence, ExifTags
import torch
import numpy as np
import hashlib

class AdvancedLoadImageFromFolder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_folder": ("STRING", {"default": ""}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image", "file_name", "metadata")
    FUNCTION = "load_image"
    CATEGORY = "image"

    def load_image(self, image_folder, index):
        if not os.path.exists(image_folder):
            raise ValueError(f"Folder does not exist: {image_folder}")

        supported_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff')
        files = [f for f in os.listdir(image_folder) if f.lower().endswith(supported_extensions)]
        
        if not files:
            raise ValueError("No supported image files found in the folder")

        # Sort files alphabetically, ignoring case for consistency across OS (fixes Linux/Windows sorting issues)
        files.sort(key=str.lower)

        if index >= len(files) or index < 0:
            raise ValueError(f"Index {index} out of range. Available images: {len(files)}")

        file_path = os.path.join(image_folder, files[index])
        img = Image.open(file_path)
        
        # Handle animated/multi-frame images
        output_images = []
        for i in ImageSequence.Iterator(img):
            i = ImageOps.exif_transpose(i)
            if i.mode == 'I':
                i = i.point(lambda x: x * (1 / 255))
            image = i.convert("RGB")
            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            output_images.append(image)
        
        if len(output_images) > 1:
            output_image = torch.cat(output_images, dim=0)
        else:
            output_image = output_images[0]

        file_name = files[index]

        # Extract metadata (PNG info or EXIF)
        metadata = {}
        if file_path.lower().endswith('.png'):
            if hasattr(img, 'info'):
                metadata = dict(img.info)
        else:
            exif = img.getexif()
            if exif:
                metadata = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}

        metadata_str = json.dumps(metadata, indent=4) if metadata else ""

        return (output_image, file_name, metadata_str)

    @classmethod
    def IS_CHANGED(cls, image_folder, index):
        # Hash folder contents + index for cache invalidation if folder changes
        folder_hash = hashlib.md5(str(os.listdir(image_folder)).encode()).hexdigest()
        return folder_hash + str(index)