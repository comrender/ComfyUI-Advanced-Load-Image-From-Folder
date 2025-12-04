# ComfyUI Advanced Load Image From Folder
<img width="1046" height="599" alt="image" src="https://github.com/user-attachments/assets/368bd935-3ebf-444b-a5a4-d71885c89279" />

A robust custom node that allows you to load images from a local directory with advanced control, metadata extraction, and support for animated formats.

I took metadata raw componenet from **ComfyUI-Crystools** and improved decoding. The node decode even more data which was not shown on windows native file viewer like lense model.

This node is designed to fix common issues found in other loaders, specifically regarding **metadata crashes (JSON serialization errors)** and **file ordering**.

## ✨ Key Features

* **Folder Iteration:** Load specific images from a folder using an `index` value (perfect for batch processing or loop workflows).
* **Metadata Extraction:** Extracts image metadata (PNG Info/Parameters, EXIF data) and outputs it as a JSON string.
    * *Fixes crashes:* Includes a sanitizer to handle binary/bytes data in EXIF tags, preventing `TypeError: Object of type bytes is not JSON serializable` errors.
* **Animated Support:** Full support for loading animated **GIFs** and multi-page **TIFFs** as batch tensors.
* **Smart Sorting:** Automatically sorts files alphabetically (case-insensitive) to ensure consistent order across different operating systems (Windows/Linux).
* **Safety Checks:** Prevents workflow crashes if the folder path is empty or invalid during initialization.

## 📦 Installation

1.  Navigate to your ComfyUI `custom_nodes` directory:
    ```bash
    cd /path/to/ComfyUI/custom_nodes/
    ```
2.  Clone this repository:
    ```bash
    git clone [https://github.com/YOUR_USERNAME/ComfyUI-Advanced-Load-Image-From-Folder.git](https://github.com/YOUR_USERNAME/ComfyUI-Advanced-Load-Image-From-Folder.git)
    ```
3.  Restart ComfyUI.

## 🚀 Usage

Search for the node **"Advanced Load Image From Folder"** in the ComfyUI menu (under `image/advanced`).

### Inputs

| Input Name | Type | Description |
| :--- | :--- | :--- |
| **image_folder** | STRING | The absolute path to the folder containing your images. |
| **index** | INT | The numeric index of the image to load. If the index exceeds the number of files, it wraps around (modulo). |

### Outputs

| Output Name | Type | Description |
| :--- | :--- | :--- |
| **image** | IMAGE | The loaded image (or batch of frames for GIFs). |
| **file_name** | STRING | The filename of the currently loaded image (e.g., `my_photo.jpg`). |
| **metadata** | STRING | A JSON-formatted string containing EXIF data or PNG info. Useful for debugging or passing to text nodes. |

## 🛠️ Supported Formats

* Images: `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`
* Animation/Multi-page: `.gif`, `.tiff`, `.tif`

## 🐛 Troubleshooting

**"Object of type bytes is not JSON serializable"**
This node includes a specific fix for this error. If you encounter it, it usually means an image has raw binary data in its EXIF tags. This node automatically converts those bytes to strings so the workflow continues without crashing.

## License

MIT
