import os
import pandas as pd
import torch
from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image

class ArmDataset(Dataset):
    def __init__(self, csv_file, img_dir, transform=None):
        self.data = pd.read_csv(csv_file)
        self.img_dir = img_dir
        self.transform = transform

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        img_name = os.path.join(self.img_dir, self.data.iloc[idx, 0])
        image = Image.open(img_name).convert('RGB')
        
        # 获取 3 个角度作为标签
        angles = self.data.iloc[idx, 1:4].values.astype('float32')
        angles = torch.tensor(angles)

        if self.transform:
            image = self.transform(image)

        return image, angles

def get_dataloader(csv_file, img_dir, batch_size=32, train=True):
    transform = transforms.Compose([
        transforms.Resize((112, 112)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    dataset = ArmDataset(csv_file, img_dir, transform=transform)
    
    # 简单的训练集/验证集划分 (80/20)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    if train:
        return torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    else:
        return torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
