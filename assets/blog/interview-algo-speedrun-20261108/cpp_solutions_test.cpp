
#include <iostream>
#include <vector>
#include <queue>
#include <set>
#include <string>
#include <initializer_list>
using namespace std;
struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x = 0) : val(x), next(nullptr) {}
};

ListNode* mergeTwoLists(ListNode* l1, ListNode* l2) {
    ListNode dummy(-1);           // 虚拟头结点，栈上分配即可
    ListNode* p = &dummy;
    ListNode* p1 = l1;
    ListNode* p2 = l2;

    while (p1 && p2) {
        if (p1->val > p2->val) {
            p->next = p2;
            p2 = p2->next;
        } else {
            p->next = p1;
            p1 = p1->next;
        }
        p = p->next;
    }
    p->next = p1 ? p1 : p2;       // 剩余部分整条接上
    return dummy.next;
}

ListNode* partition(ListNode* head, int x) {
    ListNode d1(-1), d2(-1);
    ListNode* p1 = &d1;
    ListNode* p2 = &d2;
    ListNode* p = head;

    while (p) {
        if (p->val < x) {
            p1->next = p;
            p1 = p1->next;
        } else {
            p2->next = p;
            p2 = p2->next;
        }
        ListNode* temp = p->next;   // 断开原链表中的每个节点的 next 指针
        p->next = nullptr;
        p = temp;
    }
    p1->next = d2.next;
    return d1.next;
}

ListNode* mergeKLists(vector<ListNode*>& lists) {
    if (lists.empty()) return nullptr;
    ListNode dummy(-1);
    ListNode* p = &dummy;
    // 小根堆：比较器只看 val
    auto cmp = [](ListNode* a, ListNode* b) { return a->val > b->val; };
    priority_queue<ListNode*, vector<ListNode*>, decltype(cmp)> pq(cmp);

    for (ListNode* head : lists) {
        if (head) pq.push(head);
    }
    while (!pq.empty()) {
        ListNode* node = pq.top(); pq.pop();
        p->next = node;
        if (node->next) pq.push(node->next);
        p = p->next;
    }
    return dummy.next;
}

ListNode* findFromEnd(ListNode* head, int k) {
    ListNode* p1 = head;
    for (int i = 0; i < k; i++) {  // p1 先走 k 步
        p1 = p1->next;
    }
    ListNode* p2 = head;
    while (p1) {                   // p1 和 p2 同时走 n - k 步
        p2 = p2->next;
        p1 = p1->next;
    }
    return p2;                     // p2 现在在倒数第 k 个节点
}

ListNode* middleNode(ListNode* head) {
    ListNode* slow = head;
    ListNode* fast = head;
    while (fast && fast->next) {
        slow = slow->next;        // 慢指针走一步
        fast = fast->next->next;  // 快指针走两步
    }
    return slow;                  // slow 指向中点
}

bool hasCycle(ListNode* head) {
    ListNode* slow = head;
    ListNode* fast = head;
    while (fast && fast->next) {
        slow = slow->next;
        fast = fast->next->next;
        if (slow == fast) return true;   // 相遇即有环
    }
    return false;                        // 走到末尾则无环
}

ListNode* detectCycle(ListNode* head) {
    ListNode* slow = head;
    ListNode* fast = head;
    while (fast && fast->next) {
        fast = fast->next->next;
        slow = slow->next;
        if (slow == fast) break;
    }
    if (!fast || !fast->next) return nullptr;   // 无环

    slow = head;                  // 一个指针重新指向头结点
    while (slow != fast) {        // 同速前进
        fast = fast->next;
        slow = slow->next;
    }
    return slow;                  // 相遇点就是环起点
}

ListNode* getIntersectionNode(ListNode* headA, ListNode* headB) {
    ListNode* p1 = headA;
    ListNode* p2 = headB;
    while (p1 != p2) {
        // p1 走一步；走到 A 的末尾就转到 B
        p1 = (p1 == nullptr) ? headB : p1->next;
        // p2 走一步；走到 B 的末尾就转到 A
        p2 = (p2 == nullptr) ? headA : p2->next;
    }
    return p1;                    // 相交则返回交点，否则是 nullptr
}


// ---------------- test harness ----------------
// This harness is how the C++ in the post was verified: compiled with
//   g++ -std=c++17 -Wall -Wextra -O1
// and run against the cases below.  The post's snippets assume the same
// headers as here.  Kept out of the post itself to stay readable.
static int fails = 0;
static ListNode* L(initializer_list<int> vs){ ListNode d(-1); ListNode* p=&d; for(int v:vs){p->next=new ListNode(v);p=p->next;} return d.next; }
static vector<int> show(ListNode* h){ vector<int> o; set<ListNode*> seen; while(h&&o.size()<40){ if(seen.count(h)){o.push_back(-999);break;} seen.insert(h); o.push_back(h->val); h=h->next;} return o; }
static string S(const vector<int>& v){ string s="["; for(size_t i=0;i<v.size();i++){ if(i)s+=","; s+=to_string(v[i]); } return s+"]"; }
static void check(const string& n, const vector<int>& got, const vector<int>& want){
  bool ok = got==want; cout << "    " << (ok?"OK  ":"FAIL") << " " << n << ": got " << S(got) << " want " << S(want) << "\n";
  if(!ok) fails++;
}
static void checki(const string& n, int got, int want){
  bool ok = got==want; cout << "    " << (ok?"OK  ":"FAIL") << " " << n << ": got " << got << " want " << want << "\n";
  if(!ok) fails++;
}
static ListNode* tail(ListNode* h){ while(h->next) h=h->next; return h; }

int main(){
  cout << "  -- 21 mergeTwoLists --\n";
  check("both empty", show(mergeTwoLists(nullptr,nullptr)), {});
  check("one empty", show(mergeTwoLists(L({1,2,3}),nullptr)), {1,2,3});
  check("[1,2,4]+[1,3,4]", show(mergeTwoLists(L({1,2,4}),L({1,3,4}))), {1,1,2,3,4,4});
  check("negatives", show(mergeTwoLists(L({-9,0}),L({-5,3}))), {-9,-5,0,3});

  cout << "  -- 86 partition --\n";
  check("x=3", show(partition(L({1,4,3,2,5,2}),3)), {1,2,2,4,3,5});
  check("all<x", show(partition(L({1,2}),5)), {1,2});
  check("all>=x", show(partition(L({5,6}),1)), {5,6});
  check("empty", show(partition(nullptr,3)), {});

  cout << "  -- 23 mergeKLists --\n";
  { vector<ListNode*> v{L({1,4,5}),L({1,3,4}),L({2,6})}; check("3 lists", show(mergeKLists(v)), {1,1,2,3,4,4,5,6}); }
  { vector<ListNode*> v{L({1}),nullptr,L({0})}; check("with empty", show(mergeKLists(v)), {0,1}); }
  { vector<ListNode*> v{nullptr,nullptr}; check("all empty", show(mergeKLists(v)), {}); }
  { vector<ListNode*> v{}; check("no lists", show(mergeKLists(v)), {}); }
  { vector<ListNode*> v{L({1,1}),L({1,1}),L({1,1})}; check("ties stress", show(mergeKLists(v)), {1,1,1,1,1,1}); }

  cout << "  -- 19 findFromEnd --\n";
  checki("k=2", findFromEnd(L({1,2,3,4,5}),2)->val, 4);
  checki("k=5", findFromEnd(L({1,2,3,4,5}),5)->val, 1);
  checki("k=1", findFromEnd(L({1,2,3}),1)->val, 3);

  cout << "  -- 876 middleNode --\n";
  check("odd", show(middleNode(L({1,2,3,4,5}))), {3,4,5});
  checki("even -> LATER middle", middleNode(L({1,2,3,4}))->val, 3);
  checki("single", middleNode(L({7}))->val, 7);
  checki("two", middleNode(L({1,2}))->val, 2);

  cout << "  -- 141 hasCycle --\n";
  cout << "    " << (!hasCycle(L({1,2,3}))?"OK  ":"FAIL") << " no cycle\n"; if(hasCycle(L({1,2,3}))) fails++;
  cout << "    " << (!hasCycle(L({1}))?"OK  ":"FAIL") << " single\n"; if(hasCycle(L({1}))) fails++;
  cout << "    " << (!hasCycle(nullptr)?"OK  ":"FAIL") << " empty\n"; if(hasCycle(nullptr)) fails++;
  { ListNode* c=L({3,2,0,-4}); tail(c)->next=c->next;
    cout << "    " << (hasCycle(c)?"OK  ":"FAIL") << " cycle at 1\n"; if(!hasCycle(c)) fails++; }

  cout << "  -- 142 detectCycle --\n";
  cout << "    " << (detectCycle(L({1,2,3}))==nullptr?"OK  ":"FAIL") << " no cycle -> null\n"; if(detectCycle(L({1,2,3}))) fails++;
  { ListNode* c=L({3,2,0,-4}); tail(c)->next=c; checki("cycle at head", detectCycle(c)->val, 3); }
  { ListNode* c=L({1,2}); c->next->next=c; checki("self loop", detectCycle(c)->val, 1); }
  { ListNode* c=L({1,2,3,4,5}); tail(c)->next=c->next->next; checki("cycle at idx2", detectCycle(c)->val, 3); }

  cout << "  -- 160 getIntersectionNode --\n";
  { ListNode* sh=L({8,4,5}); ListNode* A=L({4,1}); tail(A)->next=sh; ListNode* B=L({5,6,1}); tail(B)->next=sh;
    checki("intersect at 8", getIntersectionNode(A,B)->val, 8); }
  cout << "    " << (getIntersectionNode(L({2,6,4}),L({1,5}))==nullptr?"OK  ":"FAIL") << " no intersect -> null\n";
  if(getIntersectionNode(L({2,6,4}),L({1,5}))) fails++;
  { ListNode* x=L({1}); checki("same node", getIntersectionNode(x,x)->val, 1); }

  cout << "\n  RESULT: " << (fails==0 ? "ALL PASS" : to_string(fails)+" FAILURES") << "\n";
  return fails ? 1 : 0;
}
