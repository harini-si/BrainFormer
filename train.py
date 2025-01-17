import os, sys, cv2, random
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import torch
import numpy as np
import torch.nn as nn
import torch.backends.cudnn as cudnn
from torchvision import transforms

from models.BrainFormer import BrainFormer
#from models.resnet3D import resnet3D
#from models.MLP_mixer3D import MLPMixer3D
#from models.ViT3D import resnet3D
from utils.dataset import fMRIdataset, fMRIdataset_stride
from utils.logger import Logger
from utils.evaluation import compute_performance, compute_performance_class

def main():
	cudnn.benchmark = False        
	cudnn.deterministic = True

	seed = 2
	torch.manual_seed(seed)    
	torch.cuda.manual_seed(seed)       
	torch.cuda.manual_seed_all(seed)   

	random.seed(seed)
	np.random.seed(seed)
	os.environ['PYTHONHASHSEED'] = str(seed)


	sys.stdout = Logger('./log_train.txt')
	device_id = torch.device('cpu')
	###########   HYPER   ###########
	epochs = 1
	step_size = 25
	base_lr = 3e-5
	gamma = 0.7

	batch_size = 16
	class_num = 2
	##########   DATASET   ###########
	img_dir = 'data/'
	train_dataset = fMRIdataset(
		dataset_dir=img_dir, 
		ann_file='/Users/siharini/github/BrainFormer/list/list_2class/list_ADNI_train.txt', 
		size=(64, 64, 48))
	train_loader = torch.utils.data.DataLoader(dataset = train_dataset, 
		batch_size = batch_size, shuffle = True, num_workers = 0)

	val_dataset = fMRIdataset(
		dataset_dir=img_dir, 
		ann_file='/Users/siharini/github/BrainFormer/list/list_2class/list_ADNI_val.txt', 
		size=(64, 64, 48))
	val_loader = torch.utils.data.DataLoader(dataset = val_dataset, 
		batch_size = batch_size, shuffle = False, num_workers = 0)

	test_dataset = fMRIdataset(
		dataset_dir=img_dir, 
		ann_file='/Users/siharini/github/BrainFormer/list/list_2class/list_ADNI_train.txt',  
		size=(64, 64, 48))
	test_loader = torch.utils.data.DataLoader(dataset = test_dataset, 
		batch_size = batch_size, shuffle = False, num_workers = 0)

	###########   MODEL   ###########
	#model = resnet3D(depth=18, num_classes=class_num,
	#	pretrained='../resnet18-5c106cde.pth')
	#model = ViT(dim=256, image_size=(64,64,48), patch_size=8, num_classes=class_num,
	#			depth=6, heads=8, dim_head=64, mlp_dim=128)
	model, param = BrainFormer(depth=18, num_classes=class_num,
		pretrained=None)

	#model.to(device_id)
	print('model load')

	criterion = nn.CrossEntropyLoss()
	#optimizer = torch.optim.Adam(model.parameters(), lr=base_lr)
	optimizer = torch.optim.Adam(param, lr=base_lr)

	###########   TRAIN   ###########
	for epoch in range(epochs):

		lr = base_lr * (gamma ** (epoch // step_size))
		for g in optimizer.param_groups:
			g['lr'] = lr * g.get('lr_mult', 1)	

		print('-' * 10)
		print('epoch {}'.format(epoch + 1))

		running_loss, running_acc = 0.0, 0.0	
		model.train()
		for i, data in enumerate(train_loader, 1):
			#print()
			images, label, idx = data
			#convert to scalar type Double
			#images = images.type(torch.DoubleTensor)
			images = images.to(device_id)
			label = label.to(device_id)
			model=model.float()
			
			out = model(images.float())[0]

			loss = criterion(out, label)
			running_loss += loss.item() * label.size(0)

			_, pred = torch.max(out, 1)
			num_correct = (pred == label).sum()
			running_acc += num_correct.item()

			optimizer.zero_grad()
			loss.backward()
			optimizer.step()

			if i % 100 == 0:
				print('[%d/%d] iter: %d/%d. lr:%f . Loss: %.3f, Acc:%.3f'%(epoch+1, epochs, i, len(train_loader), lr, running_loss/(batch_size*i), running_acc/(batch_size*i)))
			#break

		print('start test on val set')
		model.eval()
		val_loss, preds = 0.0, []
		for i, data in enumerate(val_loader, 1):

			with torch.no_grad():

				images, label, idx = data
				images = images.to(device_id)
				label = label.to(device_id)
				model=model.float()
				out = model(images.float())[0]
				_, pred = torch.max(out, 1)
				preds.append(pred)

				loss = criterion(out, label)
				val_loss += loss.item() * label.size(0)

		val_loss = val_loss/len(val_dataset)
		preds = torch.cat(preds).cpu()
		labels = torch.tensor(val_dataset.label_list)

		accuracy, precisions, recall, F1_score = compute_performance(preds, labels, class_num=class_num)

		print('Val loss: %.3f, Acc: %.3f, precision: %.3f, recall: %.3f, F1_score: %.3f'%(val_loss, accuracy, precisions, recall, F1_score))
		print('Finish {} epoch'.format(epoch+1))
		torch.save(model.state_dict(), 'weight/Vit_medical_%03d.pth'%(epoch))
		#break

	print('start test on test set')
	model.eval()
	test_loss, preds = 0.0, []
	for i, data in enumerate(test_loader, 1):

		with torch.no_grad():

			images, label, idx = data
			images = images.to(device_id)
			label = label.to(device_id)
			model=model.float()
			out = model(images.float())[0]
			_, pred = torch.max(out, 1)
			preds.append(pred)

			loss = criterion(out, label)
			test_loss += loss.item() * label.size(0)

	test_loss = test_loss/len(test_dataset)
	preds = torch.cat(preds).cpu()
	labels = torch.tensor(test_dataset.label_list)

	accuracy, precisions, recall, F1_score = compute_performance(preds, labels, class_num=class_num)	
	print('Test loss: %.3f, Acc: %.3f, precision: %.3f, recall: %.3f, F1_score: %.3f'%(test_loss, accuracy, precisions, recall, F1_score))

	overall_acc, precisions, recalls, F1_scores, accs = compute_performance_class(preds, labels, class_num=class_num)	
	print('overall_acc:', overall_acc)
	print('accs:', accs)
	print('precisions:', precisions)
	print('recalls:', recalls)
	print('F1_scores:', F1_scores)

if __name__ == '__main__':
	main()