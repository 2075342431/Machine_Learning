import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from torch.utils.data import DataLoader, TensorDataset, random_split
import numpy as np
import matplotlib.pyplot as plt

# 1. 定义网络
class FistNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(63, 64), nn.ReLU(),
            nn.Linear(64, 32), nn.ReLU(),
            nn.Linear(32, 1), nn.Sigmoid()
        )
    def forward(self, x): return self.net(x)

def load_data(csv_path):
    df = pd.read_csv(csv_path, header=0)
    if isinstance(df.iloc[0, 0], str): 
        df = df.iloc[1:].reset_index(drop=True)
        
    features = df.iloc[:, :63].values.astype(np.float32)
    labels = df.iloc[:, 63].values.astype(np.float32).reshape(-1, 1)
    dataset = TensorDataset(torch.tensor(features), torch.tensor(labels))
    return dataset

def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = FistNet().to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.005)
    
    # --- 关键升级：划分训练集(80%)和验证集(20%) ---
    full_dataset = load_data("/home/kk/Desktop/Machine_Learning/scripts/hand_gestures.csv")
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    
    # 记录数据的列表
    train_losses, val_losses = [], []
    epochs = 80
    
    print("🚀 开始专业级训练与验证...")
    for epoch in range(epochs):
        # 1. 训练阶段
        model.train()
        epoch_train_loss = 0
        for batch_features, batch_labels in train_loader:
            batch_features, batch_labels = batch_features.to(device), batch_labels.to(device)
            optimizer.zero_grad()
            outputs = model(batch_features)
            loss = criterion(outputs, batch_labels)
            loss.backward()
            optimizer.step()
            epoch_train_loss += loss.item()
            
        avg_train_loss = epoch_train_loss / len(train_loader)
        train_losses.append(avg_train_loss)
        
        # 2. 验证阶段 (考试，不更新权重)
        model.eval()
        epoch_val_loss = 0
        with torch.no_grad():
            for batch_features, batch_labels in val_loader:
                batch_features, batch_labels = batch_features.to(device), batch_labels.to(device)
                outputs = model(batch_features)
                loss = criterion(outputs, batch_labels)
                epoch_val_loss += loss.item()
                
        avg_val_loss = epoch_val_loss / len(val_loader)
        val_losses.append(avg_val_loss)
        
        if (epoch+1) % 10 == 0:
            print(f"Epoch [{epoch+1}/{epochs}] | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")
            
    torch.save(model.state_dict(), "fist_model.pth")
    print("✅ 模型已保存")

    # --- 收集验证集的最终预测结果，用于画图 ---
    model.eval()
    all_preds, all_trues = [], []
    with torch.no_grad():
        for batch_features, batch_labels in val_loader:
            batch_features = batch_features.to(device)
            outputs = model(batch_features)
            all_preds.extend(outputs.cpu().numpy().flatten())
            all_trues.extend(batch_labels.numpy().flatten())
            
    all_preds = np.array(all_preds)
    all_trues = np.array(all_trues)
    errors = all_preds - all_trues

    # ================= 开始绘制专业分析大图 =================
    print("📊 正在生成专业分析图表三联矩阵...")
    plt.style.use('ggplot') # 使用更高级的绘图风格
    fig, axs = plt.subplots(1, 3, figsize=(18, 5)) # 创建 1行3列 的大图
    
    # 图 1：训练集 vs 验证集 Loss 曲线
    axs[0].plot(range(1, epochs + 1), train_losses, label='Train Loss', color='#1f77b4', linewidth=2)
    axs[0].plot(range(1, epochs + 1), val_losses, label='Validation Loss', color='#ff7f0e', linewidth=2)
    axs[0].set_title('Learning Curve (Overfitting Check)', fontweight='bold')
    axs[0].set_xlabel('Epochs')
    axs[0].set_ylabel('MSE Loss')
    axs[0].legend()
    
    # 图 2：真实值 vs 预测值 散点图
    axs[1].scatter(all_trues, all_preds, alpha=0.6, color='#2ca02c', edgecolor='k')
    axs[1].plot([0, 1], [0, 1], 'r--', linewidth=2) # 绘制 y=x 完美预测对角线
    axs[1].set_title('Prediction Accuracy (Ground Truth vs Pred)', fontweight='bold')
    axs[1].set_xlabel('True Label (0.0 to 1.0)')
    axs[1].set_ylabel('Model Prediction')
    axs[1].set_xlim(-0.1, 1.1)
    axs[1].set_ylim(-0.1, 1.1)
    
    # 图 3：误差分布直方图
    axs[2].hist(errors, bins=20, color='#d62728', alpha=0.7, edgecolor='black')
    axs[2].axvline(x=0, color='blue', linestyle='dashed', linewidth=2)
    axs[2].set_title('Residual Error Distribution', fontweight='bold')
    axs[2].set_xlabel('Prediction Error (Pred - True)')
    axs[2].set_ylabel('Frequency')
    
    plt.tight_layout()
    chart_name = 'professional_report_charts.png'
    plt.savefig(chart_name, dpi=300)
    print(f"📈 图表矩阵已成功保存至: {chart_name}")

if __name__ == "__main__":
    train()