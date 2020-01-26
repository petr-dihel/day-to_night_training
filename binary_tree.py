import hashlib
from functools import reduce

class PairedImage:
	
	def __init__(self):
		self.node_day = False
		self.node_night = False

	def set_day(node_day):
		self.node_day = node_day	

	def set_night(node_night):
		self.node_night = node_night

class tree_node:

	def __init__(self, hashValue, isDay, north, east, videoFileName, isFrontView):
		self.hashValue = hashValue
		self.isDay = isDay
		self.north = north
		self.east = east
		self.videoFileName = videoFileName
		self.right = False
		self.left = False
		self.isFrontView = isFrontView

	def getOpossiteHashValue(self):
		gpsString = str(self.north) + ":" + str(self.east)
		if self.isDay:
			isDay = "N"
		else:
			isDay = "D"	
		hash = hashlib.md5((str(isDay) + ":" + str(self.isFrontView) + ":" + gpsString).encode('utf-8')).hexdigest()	
		hashValue = int(hashlib.md5(hash.encode('utf-8')).hexdigest(), 16)
		return hashValue

class binary_tree:

	def __init__(self):
		self.nodes = []
		self.root = False

	def insertNode(self, node):
		if self.root == False:
			self.root = node
			self.nodes.append(node)
		else:
			self.internalInsertNode(self.root, node)

	def internalInsertNode(self, current, newNode):
		if current.hashValue < newNode.hashValue:
			if current.right == False:
				self.nodes.append(newNode)
				current.right = newNode 
			else:
				self.internalInsertNode(current.right, newNode)
		else:
			if current.left == False:
				self.nodes.append(newNode)
				current.left = newNode 
			else:
				self.internalInsertNode(current.left, newNode)				

	def loadFromFile(self, fileName):
		with open(fileName, "r") as file:
			for line in file.readlines():
				hashValue, isDay, isFront, north, east, videoFileName, line = line.split(":")
				#hashValue to number
				hashValue = int(hashlib.md5(hashValue.encode('utf-8')).hexdigest(), 16)
				isDay = (isDay == 'D')
				north = float(north)
				east = float(east)
				videoFileName = str(videoFileName)
				#line do nothing just to debug
				newNode = tree_node(hashValue, isDay, north, east, videoFileName, isFront)
				self.insertNode(newNode)

	def getNodeByHashValue(self, hashValue):
		return self.internalgetNodeByHashValue(self.root, hashValue)
		
	def internalgetNodeByHashValue(self, currentNode, hashValue):
		if self.root.hashValue == hashValue:
			return self.root
		if self.root.hashValue < hashValue:
			if currentNode.right == False:
				return False 
			else:
				return self.internalgetNodeByHashValue(currentNode.right, hashValue)
		else:
			if currentNode.left == False:
				return False
			else:
				return self.internalgetNodeByHashValue(currentNode.left, hashValue)	

	def printTree(self):
		tabs = 3
		self.internal_print(self.root, tabs, True)

	def internal_print(self, node, tabs, new_line = False):
		if tabs < 1 or tabs > 6:
			return
		for x in range(0, tabs):
			print("\t", end = '')
		if new_line:
			print(node.hashValue, end='\n\n')
		else:
			print(node.hashValue, end='')	
		if node.left != False:
			print(str(tabs) + "-L-", end='')
			if node.right == False:
				self.internal_print(node.left, tabs-1, True)
			else:
				self.internal_print(node.left, tabs-1, True)		
		if node.right != False:
			print(str(tabs) + "-R-", end='')
			self.internal_print(node.right, tabs+1, True)


binary_tree = binary_tree()
binary_tree.loadFromFile("output/log_gps.txt")

currentNode = binary_tree.root
# calculated hash of opposite time for the same location

pairedImages = []

#self gonna be really tons of data should split somehow to parts or just it will return part of paired images than another part
for node in binary_tree.nodes:
	searchedHashValue = node.getOpossiteHashValue()
	opossiteNode = binary_tree.getNodeByHashValue(searchedHashValue)
	if opossiteNode != False:	
		break	
		newPairedImage = PairedImage()			
		if node.isDay:
			newPairedImage.node_day = node
			newPairedImage.node_night = opossiteNode
		else:
			newPairedImage.node_day = opossiteNode
			newPairedImage.node_night = node
		pairedImages.append(newPairedImage)

print("Prepared paired images to training : " + str(len(pairedImages)))

#for newPairedImage in pairedImages:
	#todo machine learning shit or return paireded images and do AI learning shit in another file			

