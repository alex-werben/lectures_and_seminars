class ListNode:
	def __init__(self, val=0, next=None):
		self.val = val
		self.next = next
def solution(l1: ListNode, l2: ListNode) -> ListNode:
	"""Объединяет два отсортированных связанных списка и возвращает новый отсортированный список."""
	dummy = ListNode()
	current = dummy
	while l1 and l2:
		if l1.val < l2.val:
			current.next = l1
			l1 = l1.next
		else:
			current.next = l2
			l2 = l2.next
		current = current.next
	current.next = l1 or l2
	return dummy.next
if __name__ == '__main__':
	# Тестовые случаи
	def print_list(node):
		while node:
			print(node.val, end=' -> ')
			node = node.next
		print('None')
	node1 = ListNode(1, ListNode(2, ListNode(4)))
	node2 = ListNode(1, ListNode(3, ListNode(4)))
	merged_list = solution(node1, node2)
	print_list(merged_list)