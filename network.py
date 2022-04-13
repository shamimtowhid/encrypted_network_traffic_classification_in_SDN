import torch.nn as nn
import torch.nn.functional as F

class Net(nn.Module):
    def __init__(self, num_class):
        super().__init__()
        self.conv1 = nn.Conv1d(4, 512, kernel_size=3, stride=1, padding=1, bias=True)
        self.bn1 = nn.BatchNorm1d(512)
        
        self.conv2 = nn.Conv1d(512, 256, kernel_size=3, stride=1, padding=1, bias=True)
        self.bn2 = nn.BatchNorm1d(256)
#         self.relu = nn.LeakyReLU(inplace=True)
        
        self.conv3 = nn.Conv1d(256, 128, kernel_size=3, stride=1, padding=1, bias=True)
        self.bn3 = nn.BatchNorm1d(128)
#         self.relu = nn.LeakyReLU(inplace=True)

        self.relu = nn.LeakyReLU(inplace=True)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Linear(128, num_class)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        
        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        
        x = self.conv3(x)
        x = self.bn3(x)
        x = self.relu(x)
        
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        
        return x
