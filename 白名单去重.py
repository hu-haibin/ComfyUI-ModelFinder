import json
import os
import re
import struct
from datetime import datetime
from typing import Dict, List

# --- 白名单配置 ---
MODEL_NODE_TYPES = [
    # --- 基础加载器 ---
    "CheckpointLoader", "CheckpointLoaderSimple", "UNETLoader", "VAELoader", 
    "CLIPLoader", "CLIPVisionLoader", "DualCLIPLoader", "TripleCLIPLoader",
    "ModelLoader", "GANLoader", "UpscaleModelLoader", "Upscale Model Loader",
    "StyleModelLoader", "ControlNetLoader", "ControlNetLoaderAdvanced",
    "DiffControlNetLoader", "LoraLoader", "LoraLoaderModelOnly",
    "ACN_ControlNetLoaderAdvanced", "UnetLoaderGGUF", # 新增：GGUF 专用加载

    # --- Qwen / Janus / Vision / LLM 专项 ---
    "JanusModelLoader", "JanusProModelLoader", "JanusProModelLoader|Mie", # 新增：JanusPro 变体
    "Qwen2.5VL", "Qwen2.5", "Qwen2_VQA", "Qwen3_VQA", 
    "NunchakuQwenImageDiTLoader", "DownloadAndLoadQwenModel", 
    "LoadWanVideoClipTextEncoder", "LoadWanVideoT5TextEncoder",
    "LibLibVision", "LibLibVisionV2Seed", "LibLibVisionV2Qwen", "LibLibSeedreamNode", 
    "LibLibSeedreamV4Node", "GeminiImageNode", "GeminiImage2Node", 
    "LibLibGenerate", 

    # --- Flux / Nunchaku / Kontext ---
    "NunchakuTextEncoderLoader", "NunchakuTextEncoderLoaderV2", "NunchakuFluxDiTLoader", 
    "NunchakuFluxLoraLoader", "PulidFluxModelLoader", "FluxLoraLoader",
    "FluxKontextProImageNode", "FluxKontextMaxImageNode", "IPAdapterFluxLoader",

    # --- 视频 / 帧内插 / 音频数字人 ---
    "WanVideoModelLoader", "WanVideoVAELoader", "WanVideoVACEModelSelect", 
    "WanVideoLoraSelect", "WanVideoLoraSelectMulti", "WanVideoTextEncodeCached",
    "ADE_AnimateDiffLoaderWithContext", 
    "ADE_LoadAnimateDiffModel", "DownloadAndLoadGIMMVFIModel", "RIFE VFI",
    "DownloadAndLoadWav2VecModel", "MultiTalkModelLoader", "SparkTTSClone", # 新增：音频/驱动模型
    "IndexTTS2Run", # 新增：语音克隆执行器
    "WanVideoUni3C_ControlnetLoader", # 新增：Wan 视频 ControlNet 加载器

    # --- 换脸 / 人像 ---
    "ReActorFaceSwap", "ReActorBuildFaceModel", "PulidModelLoader", 
    "EcomID_PulidModelLoader", "InstantIDModelLoader", "InstantID_IPA_ModelLoader",
    "FaceAnalysisModels", "InstantIDFaceAnalysis", "EcomIDFaceAnalysis",
    "FaceProcessorLoader", "FaceRestoreModelLoader", "FaceParsingModelLoader(FaceParsing)",
    "PulidInsightFaceLoader", "PulidFluxInsightFaceLoader", "FaceBoundingBox",
    "FaceSegmentation", "CropFace",

    # --- 抠图 / 遮罩 ---
    "SAMLoader", "SAMModelLoader (segment anythi)", "DownloadAndLoadSAM2Model",
    "GroundingDinoModelLoader (segment anythi)", "GroundingDinoSAMSegment (segme)",
    "LayerMask: LoadBiRefNetModel", "LayerMask: LoadBiRefNetModelV2", 
    "LayerMask: BiRefNetUltra", "LayerMask: BiRefNetUltraV2",
    "LayerMask: SegmentAnythingUltr", "LayerMask: PersonMaskUltra", 
    "LayerMask: PersonMaskUltra V2", "LayerMask: SegformerB2ClothesU",
    "LayerMask: SAM2VideoUltra", "RMBG", "InspyrenetRembg", "LayerMask: RmBgUltra V2",
    "BiRefNet_Hugo", "easy imageRemBg", "LayerMask: MaskEdgeUltraDetail", # 新增：多种抠图变体

    # --- 缩放 / 修复 ---
    "SUPIR_Upscale", "SUPIR_model_loader_v2", "HYPIRAdvancedRestoration",
    "Florence2ModelLoader", "DownloadAndLoadFlorence2Model", "LayerMask: LoadFlorence2Model",
    "Florence2Run", "ApplyStableSRUpscaler", "AuraSR.AuraSRUpscaler",
    "APISR_ModelLoader_Zho", "AdvancedVisionLoader", "Joy_caption_load", 
    "Joy_caption_two_load", "LayerUtility: LoadJoyCaptionBe", "LayerUtility: LaMa",
    "LayerUtility: PhiPrompt",

    # --- 预处理器 / 专项加载 ---
    "DWPreprocessor", "DepthAnythingPreprocessor", "DepthAnythingV2Preprocessor",
    "AIO_Preprocessor", "AV_ControlNetPreprocessor", "AnyLineArtPreprocessor_aux", 
    "LineArtPreprocessor", "DownloadAndLoadDepthAnythingV2", 
    "UltralyticsDetectorProvider", "SAMModelLoader", "SAM2ModelLoader",
    "BrushNetLoader", "PowerPaintCLIPLoader", "LoadAndApplyICLightUnet", 
    "LoadICLightUnetDiffusers", "INPAINT_LoadFooocusInpaint", "INPAINT_LoadInpaintModel", 
    "SeedVR2", "SeedVR2LoadVAEModel", "SeedVR2LoadDiTModel", "AudioEncoderLoader",
    "ControlNetInpaintingAliMamaApp", "Miaoshouai_Tagger", "WD14Tagger|pysssss"
]

NODE_MODEL_INDICES = {
    "default": [0],
    
    # --- 基础/多 CLIP 加载 ---
    "DualCLIPLoader": [0, 1],
    "TripleCLIPLoader": [0, 1, 2],
    
    # --- 多模型加载节点 ---
    "SUPIR_Upscale": [0, 1],                    
    "ReActorFaceSwap": [1, 3],                  
    "DWPreprocessor": [4, 5],                   
    "LayerMask: SegmentAnythingUltr": [0, 1],   
    "NunchakuTextEncoderLoader": [1, 2],        
    "NunchakuTextEncoderLoaderV2": [1, 2],
    "HYPIRAdvancedRestoration": [4, 5],
    "WanVideoLoraSelectMulti": [0, 2, 4, 6],
    "PowerPaintCLIPLoader": [0, 1],             
    "IPAdapterFluxLoader": [0, 1],              

    # --- 视觉/在线/LLM 节点 ---
    "LibLibVision": [1],
    "LibLibVisionV2Seed": [1],
    "LibLibVisionV2Qwen": [1],
    "LibLibSeedreamNode": [1],
    "LibLibSeedreamV4Node": [1],
    "GeminiImageNode": [1],
    "GeminiImage2Node": [1],
    "Qwen2.5VL": [1],                           
    "Qwen2.5": [1],
    "Qwen2_VQA": [1],
    "LibLibGenerate": [2],
    "LayerUtility: PhiPrompt": [0],

    # --- 音频/驱动专项 (根据报告校对) ---
    "SparkTTSClone": [1],                       # 索引1位置是音色名/模型标识
    "MultiTalkModelLoader": [0],                # 对应 InfiniTetalk 权重文件
    "DownloadAndLoadWav2VecModel": [0],         # 对应 Wav2Vec 路径
    
    # --- 预处理器与专项工具 ---
    "UltralyticsDetectorProvider": [0],         
    "InstantID_IPA_ModelLoader": [0],
    "CropFace": [0],                            
    "LayerUtility: LaMa": [0],                  
    "PulidInsightFaceLoader": [0],
    "PulidFluxInsightFaceLoader": [0],
    "FaceAnalysisModels": [0],
    "InstantIDFaceAnalysis": [0],
    "EcomIDFaceAnalysis": [0],
    "AIO_Preprocessor": [0],                    
    "AV_ControlNetPreprocessor": [0],           
    "AnyLineArtPreprocessor_aux": [0],
    "LineArtPreprocessor": [0],
    "DownloadAndLoadDepthAnythingV2": [0],      
    "ACN_ControlNetLoaderAdvanced": [0],        
    "LayerUtility: LoadJoyCaptionBe": [0],      
    "LayerMask: MaskEdgeUltraDetail": [0],      # 提取报告中的 VITMatte 等模型
    "WanVideoTextEncodeCached": [0],            # 文本编码器模型
    "WanVideoUni3C_ControlnetLoader": [0],      # Wan 视频 ControlNet
    "OnnxDetectionModelLoader": [0, 1],         # vitpose_model, yolo_model

    # --- 排除干扰节点 ---
    "FluxKontextProImageNode": [],
    "FluxKontextMaxImageNode": [],
    "LibLibTranslate": [],
    "LibLibOptions": [],
    "Florence2Run": [],                         
    "LayerMask: MaskPreview": [],
    "IndexTTS2Run": []                          # 报告显示该节点主要处理参数，模型通常固定或通过API
}
def clean_path(path: str) -> str:
    return path.strip().strip('&').strip().strip('"').strip("'")

def read_png_workflow(file_path):
    try:
        with open(file_path, 'rb') as f:
            if f.read(8) != b'\x89PNG\r\n\x1a\n': return None
            while True:
                chunk_hdr = f.read(8)
                if not chunk_hdr or len(chunk_hdr) < 8: break
                length, chunk_type = struct.unpack('>I4s', chunk_hdr)
                if chunk_type in [b'tEXt', b'iTXt']:
                    data = f.read(length)
                    for p in data.split(b'\x00'):
                        try:
                            decoded = p.decode('utf-8', errors='ignore')
                            if '{' in decoded: return json.loads(decoded)
                        except: continue
                else: f.seek(length, 1)
                f.read(4)
    except: return None

def log_and_print(msg, log_file):
    print(msg)
    log_file.write(msg + "\n")

def process_single_file(path, log_file):
    data = None
    try:
        if path.lower().endswith(".json"):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
        elif path.lower().endswith(".png"):
            data = read_png_workflow(path)
        
        if not data: return

        nodes = data.get("nodes", [])
        if not nodes and isinstance(data, dict):
            nodes = data.values()

        found_info = []
        seen_in_file = set()

        for node in nodes:
            if not isinstance(node, dict): continue
            node_type = node.get("type") or node.get("class_type", "")
            widgets = node.get("widgets_values", [])
            snr_name = node.get("properties", {}).get("Node name for S&R") or node_type

            if node_type in MODEL_NODE_TYPES or "Loader" in node_type:
                indices = NODE_MODEL_INDICES.get(node_type, NODE_MODEL_INDICES["default"])
                for idx in indices:
                    if len(widgets) > idx:
                        val = str(widgets[idx])
                        if val.lower() in ["none", "auto", "default", "disable"]: continue
                        
                        model_filename = os.path.basename(val.replace("\\", "/"))
                        entry_id = f"{snr_name}||{node_type}||{model_filename}"
                        
                        if entry_id not in seen_in_file:
                            found_info.append(f"{snr_name:<35} | {node_type:<35} | {model_filename}")
                            seen_in_file.add(entry_id)

        if found_info:
            log_and_print(f"\n📂 工作流: {os.path.basename(path)}", log_file)
            log_and_print("-" * 110, log_file)
            for info in found_info:
                log_and_print(info, log_file)
            log_and_print("-" * 110, log_file)

    except Exception as e:
        log_and_print(f"❌ 处理 {os.path.basename(path)} 时出错: {e}", log_file)

def start_session(user_input):
    paths = []
    if user_input.startswith('"') and '" "' in user_input:
        paths = [clean_path(p) for p in re.findall(r'"([^"]+)"', user_input)]
    else:
        paths = [clean_path(user_input)]

    if not paths: return

    # 生成日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    first_path = paths[0]
    base_name = os.path.basename(first_path.rstrip(os.sep))
    log_filename = f"{timestamp}_{base_name}_模型映射报告.txt"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(script_dir, log_filename)

    with open(log_path, "w", encoding="utf-8") as log_file:
        header_text = f"ComfyUI 模型映射 SOP 导出报告\n生成的 S&R 参考列表\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        log_and_print("=" * 110, log_file)
        log_and_print(header_text, log_file)
        log_and_print(f"{'Node name for S&R':<35} | {'原节点类型':<35} | {'模型文件名'}", log_file)
        log_and_print("=" * 110, log_file)

        for p in paths:
            if not os.path.exists(p): continue
            if os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for file in files:
                        if file.lower().endswith(('.json', '.png')):
                            process_single_file(os.path.join(root, file), log_file)
            else:
                process_single_file(p, log_file)

        log_and_print(f"\n✅ 扫描完成！报告已保存至: {log_path}", log_file)

if __name__ == "__main__":
    print("====================================================")
    print("   ComfyUI 模型映射 SOP 工具 (TXT 增强版)")
    print("   支持多文件/文件夹混拖，自动生成映射文档")
    print("====================================================")
    while True:
        raw_input = input("\n请拖入文件/文件夹 (q 退出): ").strip()
        if raw_input.lower() == 'q': break
        if not raw_input: continue
        start_session(raw_input)