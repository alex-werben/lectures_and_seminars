from generated_script import solution, ListNode

def test_solution():
    # Тестовый случай 1: Оба списка пусты
    assert solution(None, None) is None
    
    # Тестовый случай 2: Один список пуст
    node1 = ListNode(1)
    assert solution(node1, None).val == 1
    assert solution(None, node1).val == 1
    
    # Тестовый случай 3: Оба списка имеют один элемент каждый
    node1 = ListNode(1)
    node2 = ListNode(2)
    merged_list = solution(node1, node2)
    assert merged_list.val == 1
    assert merged_list.next.val == 2
    
    # Тестовый случай 4: Оба списка имеют несколько элементов
    node1 = ListNode(1, ListNode(3, ListNode(5)))
    node2 = ListNode(2, ListNode(4, ListNode(6)))
    merged_list = solution(node1, node2)
    expected_values = [1, 2, 3, 4, 5, 6]
    for val in expected_values:
        assert merged_list.val == val
        merged_list = merged_list.next
    
    # Тестовый случай 5: Один список полностью меньше другого
    node1 = ListNode(1)
    node2 = ListNode(2, ListNode(3))
    merged_list = solution(node1, node2)
    expected_values = [1, 2, 3]
    for val in expected_values:
        assert merged_list.val == val
        merged_list = merged_list.next