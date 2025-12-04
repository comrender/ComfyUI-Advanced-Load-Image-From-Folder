import os
import json
import hashlib
from PIL import Image, ImageOps, ImageSequence, ExifTags
from PIL.PngImagePlugin import PngImageFile
from PIL.JpegImagePlugin import JpegImageFile
import torch
import numpy as np
from datetime import datetime
from pathlib import Path
import piexif

class AdvancedLoadImageFromFolder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_folder": ("STRING", {"default": "", "multiline": False}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "METADATA_RAW")
    RETURN_NAMES = ("image", "file_name", "Metadata RAW")
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

        # Load image
        img = Image.open(file_path)
        
        # --- Metadata Extraction ---
        metadata = self.get_metadata(file_path, img)

        # Standardize Orientation
        img = ImageOps.exif_transpose(img)

        # Convert to tensor (supports GIF/TIFF animation)
        frames = []
        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("RGB")
            arr = np.array(frame).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr)[None, ...]
            frames.append(tensor)
        image_out = torch.cat(frames, dim=0) if len(frames) > 1 else frames[0]

        name_without_ext = os.path.splitext(selected_file)[0]

        return (image_out, name_without_ext, metadata)

    def get_metadata(self, image_path, img):
        metadata = {}

        # 1. Standard FileInfo
        stat = os.stat(image_path)
        metadata["fileinfo"] = {
            "filename": Path(image_path).as_posix(),
            "resolution": f"{img.width}x{img.height}",
            "date": str(datetime.fromtimestamp(stat.st_mtime)),
            "size": str(stat.st_size),
        }

        # 2. WebP Handling (Using piexif)
        if img.format == 'WEBP':
            try:
                exif_data = piexif.load(image_path)
                self.process_exif_data(exif_data, metadata)
            except Exception as e:
                print(f"Error parsing WebP EXIF: {e}")

        # 3. PNG Handling
        if isinstance(img, PngImageFile):
            metadataFromImg = img.info
            for k, v in metadataFromImg.items():
                if k == "workflow":
                    try:
                        metadata["workflow"] = json.loads(v)
                    except:
                        metadata["workflow"] = v
                elif k == "prompt":
                    try:
                        metadata["prompt"] = json.loads(v)
                    except:
                        metadata["prompt"] = v
                else:
                    try:
                        metadata[str(k)] = json.loads(v)
                    except:
                        metadata[str(k)] = str(v)

        # 4. JPEG / Standard Exif Handling
        if isinstance(img, JpegImageFile) or img.format in ['JPG', 'JPEG']:
            exif = img.getexif()
            if exif:
                for k, v in exif.items():
                    tag = ExifTags.TAGS.get(k, k)
                    tag_name = str(tag)
                    
                    # --- FIX: Handle XP Tags (Windows-specific UTF-16LE) ---
                    if isinstance(v, bytes) and tag_name.startswith("XP"):
                        try:
                            # XP tags are UTF-16LE, often with double null terminators.
                            # We decode safely and remove nulls.
                            metadata[tag_name] = v.decode('utf-16le').replace('\x00', '')
                        except:
                            metadata[tag_name] = str(v)
                            
                    # --- FIX: Handle UserComment (Header stripping) ---
                    elif isinstance(v, bytes) and tag_name == "UserComment":
                        try:
                            # UserComment often has an 8-byte character code header
                            prefix = v[:8]
                            data = v[8:]
                            if prefix.startswith(b'UNICODE'):
                                metadata[tag_name] = data.decode('utf-16le', errors='ignore').replace('\x00', '')
                            elif prefix.startswith(b'ASCII'):
                                metadata[tag_name] = data.decode('ascii', errors='ignore').replace('\x00', '')
                            else:
                                # Try UTF-8 fallback, then raw decode
                                try:
                                    metadata[tag_name] = v.decode('utf-8').replace('\x00', '')
                                except:
                                    metadata[tag_name] = v.decode('utf-16le', errors='ignore').replace('\x00', '')
                        except:
                             metadata[tag_name] = str(v)

                    # Standard handling for everything else
                    elif v is not None:
                         metadata[tag_name] = str(v)
                
                # GPS Handling
                for ifd_id in ExifTags.IFD:
                    try:
                        if ifd_id == ExifTags.IFD.GPSInfo:
                            resolve = ExifTags.GPSTAGS
                        else:
                            resolve = ExifTags.TAGS
                        
                        ifd = exif.get_ifd(ifd_id)
                        ifd_name = str(ifd_id.name)
                        
                        if ifd:
                            metadata[ifd_name] = {}
                            for k, v in ifd.items():
                                tag = resolve.get(k, k)
                                metadata[ifd_name][str(tag)] = str(v)
                    except KeyError:
                        pass

        # 5. Human Readable Camera Info
        self.extract_camera_info(metadata)
        
        return metadata

    def process_exif_data(self, exif_data, metadata):
        if '0th' in exif_data:
            if 271 in exif_data['0th']:
                prompt_data = exif_data['0th'][271].decode('utf-8')
                prompt_data = prompt_data.replace('Prompt:', '', 1)
                try:
                    metadata['prompt'] = json.loads(prompt_data)
                except json.JSONDecodeError:
                    metadata['prompt'] = prompt_data
            
            if 270 in exif_data['0th']:
                workflow_data = exif_data['0th'][270].decode('utf-8')
                workflow_data = workflow_data.replace('Workflow:', '', 1)
                try:
                    metadata['workflow'] = json.loads(workflow_data)
                except json.JSONDecodeError:
                    metadata['workflow'] = workflow_data
        metadata.update(exif_data)

    def extract_camera_info(self, metadata):
        camera = {}
        def g(tag, default=None): return metadata.get(tag, default)

        make = str(g("Make", "")).strip()
        model = str(g("Model", "")).strip()
        camera["Camera"] = f"{make} {model}".strip() or "Unknown Camera"

        lens = g("LensModel") or g("LensType") or g("Lens")
        if lens and str(lens).strip(): camera["Lens"] = str(lens).strip()

        fnum = g("FNumber")
        if isinstance(fnum, tuple): fnum = fnum[0]/fnum[1] if fnum[1] else 0
        if fnum: camera["Aperture"] = f"f/{float(fnum):.1f}".rstrip("0").rstrip(".")

        exp = g("ExposureTime")
        if isinstance(exp, tuple): exp = exp[0]/exp[1] if exp[1] else 0
        if exp:
            if exp < 1: camera["Shutter"] = f"1/{int(round(1/exp))}s"
            else: camera["Shutter"] = f"{exp:.2f}s".rstrip("0").rstrip(".")

        iso = g("ISOSpeedRatings") or g("ISO")
        if iso: camera["ISO"] = str(iso)

        focal = g("FocalLength")
        if isinstance(focal, tuple): focal = focal[0]/focal[1] if focal[1] else 0
        if focal: camera["Focal Length"] = f"{float(focal):.0f}mm"

        camera_info = {k: v for k, v in camera.items() if v and str(v).strip()}
        if camera_info:
            metadata["Camera Info"] = camera_info

    @classmethod
    def IS_CHANGED(cls, image_folder: str, index: int):
        if not image_folder or not os.path.isdir(image_folder):
            return "invalid"
        try:
            files = [f for f in os.listdir(image_folder) if os.path.isfile(os.path.join(image_folder, f))]
            files.sort(key=str.lower)
            hash_val = hashlib.md5(''.join(files).encode()).hexdigest()
            mtime = max(os.path.getmtime(os.path.join(image_folder, f)) for f in files)
            return f"{hash_val}_{mtime}_{index}"
        except:
            return "error"

NODE_CLASS_MAPPINGS = {
    "Advanced Load Image From Folder": AdvancedLoadImageFromFolder
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Advanced Load Image From Folder": "Advanced Load Image From Folder"
}
