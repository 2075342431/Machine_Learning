import torch
from train import FistNet # 导入你之前写的网络结构

model = FistNet()
model.load_state_dict(torch.load("fist_model.pth"))
model.eval()

# 创建一个假的输入张量 (1个批次，63个特征)
dummy_input = torch.randn(1, 63)

# 导出为 ONNX
torch.onnx.export(model, dummy_input, "fist_model.onnx", 
                  export_params=True, opset_version=11, 
                  input_names=['hand_landmarks'], output_names=['fist_degree'])
print("模型已成功导出为 ONNX 格式！")