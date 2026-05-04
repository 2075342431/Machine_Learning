import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from torch.utils.data import DataLoader, TensorDataset
import numpy as np

# 1. 定义极其轻量的 MLP 网络
class FistNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(63, 64),   # 输入层：63个坐标特征
            nn.ReLU(),           # 激活函数
            nn.Linear(64, 32),   # 隐藏层
            nn.ReLU(),
            nn.Linear(32, 1),    # 输出层：1个值
            nn.Sigmoid()         # 极其关键：将输出强行压缩到 0.0 到 1.0 之间
        )

    def forward(self, x):
        return self.net(x)

# 2. 加载数据
def load_data(csv_path):
    df = pd.read_csv(csv_path, header=0)
    features = df.iloc[:, :63].values.astype(np.float32) # 前63列是坐标
    labels = df.iloc[:, 63].values.astype(np.float32).reshape(-1, 1) # 最后一列是标签
    
    dataset = TensorDataset(torch.tensor(features), torch.tensor(labels))
    return DataLoader(dataset, batch_size=32, shuffle=True)

# 3. 训练脚本
def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = FistNet().to(device)
    criterion = nn.MSELoss() # 均方误差
    optimizer = optim.Adam(model.parameters(), lr=0.01) # 学习率可以稍微大点
    
    loader = load_data("/home/kk/Desktop/Machine_Learning/scripts/hand_gestures.csv") # 替换为你的数据路径
    
    print("开始训练...")
    for epoch in range(50): # 这种小网络 50 轮就足够收敛了
        total_loss = 0
        for batch_features, batch_labels in loader:
            batch_features, batch_labels = batch_features.to(device), batch_labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_features)
            loss = criterion(outputs, batch_labels)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        if (epoch+1) % 10 == 0:
            print(f"Epoch {epoch+1}/50, Loss: {total_loss/len(loader):.4f}")
            
    torch.save(model.state_dict(), "fist_model.pth")
    print("模型已保存为 fist_model.pth")

if __name__ == "__main__":
    train()