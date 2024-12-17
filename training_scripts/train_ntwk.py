import torch
import torch.nn as nn
import torchvision
from torchvision.models import resnet18
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import os

EMBEDDING_SIZE = 256

model = resnet18(weights=torchvision.models.ResNet18_Weights.IMAGENET1K_V1)

num_features = model.fc.in_features
model.fc = nn.Linear(num_features, EMBEDDING_SIZE)

class AlbumDataset(Dataset):
    def __init__(self, root_dir, anchor_transform, positive_transform):
        self.root_dir = root_dir
        self.image_paths = [os.path.join(root_dir, fname) for fname in os.listdir(root_dir)]
        self.anchor_transform = anchor_transform
        self.positive_transform = positive_transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        image = Image.open(img_path).convert('RGB')
        
        # Apply separate transforms for anchor and positive
        anchor = self.anchor_transform(image)
        positive = self.positive_transform(image)
        
        return anchor, positive, idx

# Augmentation transforms for anchor and positive
anchor_transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),  # Random crop
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

positive_transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.RandomResizedCrop(224, scale=(0.6, 1.0)),  # Random crop
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1),  # Distortion
    transforms.RandomChoice([
        transforms.Compose([]),  # No-op (do nothing)
        transforms.RandomRotation((90, 90)),
        transforms.RandomRotation((180, 180)),
        transforms.RandomRotation((270, 270))
    ]),
    transforms.RandomRotation(degrees=5),
    transforms.RandomErasing(p=0.5, scale=(0.02, 0.10), ratio=(0.3, 3.3)),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Data loader
dataset = AlbumDataset(root_dir='album_covers_512/', anchor_transform=anchor_transform, positive_transform=positive_transform)
dataloader = DataLoader(dataset, batch_size=128, shuffle=True, num_workers=4, pin_memory=True)

import torch.optim as optim
from torch.nn.functional import normalize
from tqdm import tqdm
from datetime import datetime

# Triplet loss
triplet_loss_fn = nn.TripletMarginLoss(margin=1.0, p=2)

# Optimizer
optimizer = optim.Adam(model.parameters(), lr=1e-4, weight_decay=1e-5)

# Training loop
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

losses = []

num_epochs = 100
for epoch in range(num_epochs):
    model.train()
    epoch_loss = 0
    print(f"Starting Epoch {epoch+1}/{num_epochs} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for batch_idx, (anchors, positives, indices) in enumerate(tqdm(dataloader, desc="Processing batches")):
        anchors, positives = anchors.to(device), positives.to(device)

        # Forward pass
        anchor_emb = normalize(model(anchors), p=2, dim=1)
        positive_emb = normalize(model(positives), p=2, dim=1)

        # Generate random negatives from the batch
        negatives = anchors[torch.randperm(len(anchors))].to(device)
        negative_emb = normalize(model(negatives), p=2, dim=1)

        # Compute triplet loss
        loss = triplet_loss_fn(anchor_emb, positive_emb, negative_emb)
        epoch_loss += loss.item()

        # Backprop and optimize
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # Log batch progress
        print(f"[Epoch {epoch+1}/{num_epochs}, Batch {batch_idx+1}] Loss: {loss.item():.4f}")

    losses.append(epoch_loss)

    print(f"Epoch {epoch+1} completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, Average Loss: {epoch_loss/len(dataloader):.4f}\n")

torch.save(model.state_dict(), "tuned.pth")
print("Model training complete. Final model saved to tuned.pth")
