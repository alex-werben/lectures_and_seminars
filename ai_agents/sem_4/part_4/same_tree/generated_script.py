from typing import Optional

class TreeNode:
	def __init__(self, value=0, left=None, right=None):
		self.value = value
		self.left = left
		self.right = right

def solution(root1: Optional[TreeNode], root2: Optional[TreeNode]) -> bool:
	"""
	Рекурсивная функция для сравнения двух деревьев.
	Возвращает True, если оба дерева идентичны, иначе False.
	"""
	if not root1 and not root2:
		return True
	if not root1 or not root2:
		return False
	return root1.value == root2.value and solution(root1.left, root2.left) and solution(root1.right, root2.right)

# Тестовые случаи
if __name__ == '__main__':
	tree1 = TreeNode(1, TreeNode(2), TreeNode(3))
	tree2 = TreeNode(1, TreeNode(2), TreeNode(3))
	tree3 = TreeNode(1, TreeNode(2), TreeNode(4))
	print(solution(tree1, tree2))  # Ожидается: True
	print(solution(tree1, tree3))  # Ожидается: False