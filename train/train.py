import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models
from dataset import get_dataloader
import os

# --- 配置区 ---
DATA_DIR = '/home/kk/Desktop/Machine_Learning/data'
CSV_FILE = os.path.join(DATA_DIR, 'labels.csv')
IMG_DIR = os.path.join(DATA_DIR, 'images')
MODEL_SAVE_PATH = '/home/kk/Desktop/Machine_Learning/train/best_model.pth'

BATCH_SIZE = 32
EPOCHS = 20
LEARNING_RATE = 0.001
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def train():
    # 1. 准备数据
    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file not found at {CSV_FILE}. Please collect data first.")
        return

    train_loader = get_dataloader(CSV_FILE, IMG_DIR, batch_size=BATCH_SIZE, train=True)
    val_loader = get_dataloader(CSV_FILE, IMG_DIR, batch_size=BATCH_SIZE, train=False)

    # 2. 定义模型 (ResNet18)
    model = models.resnet18(weights=None) # 不使用预训练权重，从头训练
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, 3) # 修改输出层为 3 维角度
    model = model.to(DEVICE)

    # 3. 损失函数与优化器
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    # 4. 训练循环
    best_val_loss = float('inf')

    print(f"Starting training on {DEVICE}...")
    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * images.size(0)

        # 验证
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(DEVICE), labels.to(DEVICE)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * images.size(0)

        avg_train_loss = train_loss / len(train_loader.dataset)
        avg_val_loss = val_loss / len(val_loader.dataset)

        print(f"Epoch [{epoch+1}/{EPOCHS}] - Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")

        # 保存最优模型
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print(f"--> Saved best model with loss {best_val_loss:.4f}")

    print("Training Complete.")

if __name__ == "__main__":
    train()
