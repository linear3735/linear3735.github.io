// Harness for _posts/2026-11-16-hash-and-heap.md.
//
// This file is NOT part of the article.  verify_code.py concatenates the
// article's ```cpp blocks in front of it, compiles the result with
//
//     g++ -std=c++17 -Wall -Wextra -Werror
//
// and runs it.  Everything here exists to falsify a claim the prose makes:
// each structure is driven against an independent reference implementation
// (std::unordered_map, std::set, std::priority_queue, std::sort, or a plain
// O(n) brute force), and the boundary cases named in the post -- empty,
// single element, all equal, duplicate keys, out of range -- are all covered.
#include <algorithm>
#include <cstddef>
#include <iostream>
#include <limits>
#include <list>
#include <map>
#include <numeric>
#include <queue>
#include <random>
#include <set>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

// ------------------------------------------------------------- assertions
static long long g_checks = 0;
static int g_fail = 0;

static void report(bool ok, const char* what) {
    ++g_checks;
    if (!ok) {
        ++g_fail;
        std::cout << "       FAIL " << what << "\n";
    }
}

#define CHECK(cond) report((cond), #cond)

template <typename A, typename B>
static void checkEq(const A& a, const B& b, const char* ea, const char* eb,
                    int line) {
    ++g_checks;
    if (!(a == b)) {
        ++g_fail;
        std::cout << "       FAIL line " << line << ": " << ea << " == " << eb
                  << "  (got " << a << " vs " << b << ")\n";
    }
}
#define CHECK_EQ(a, b) checkEq((a), (b), #a, #b, __LINE__)

// The same mixed FNV-1a that ConsistentHash uses -- its own hashOf is private,
// so the plain-modulo contrast below has to re-implement it.  Used only there.
static std::size_t fnv1a(const std::string& s) {
    std::size_t h = 1469598103934665603ULL;
    for (const char ch : s) {
        h ^= static_cast<unsigned char>(ch);
        h *= 1099511628211ULL;
    }
    h ^= h >> 33;
    h *= 0xff51afd7ed558ccdULL;
    h ^= h >> 33;
    h *= 0xc4ceb9fe1a85ec53ULL;
    h ^= h >> 33;
    return h;
}

// Keys must be DISTINCT: the harness deletes in strides, and a repeated key
// would make the second remove() legitimately return false.  Keeping the index
// in the key guarantees uniqueness while the random part still spreads the
// hashes out.
static std::vector<std::string> genKeys(std::mt19937_64& rng, std::size_t n) {
    std::vector<std::string> keys;
    keys.reserve(n);
    for (std::size_t i = 0; i < n; ++i) {
        keys.push_back("key-" + std::to_string(rng() % 1000000) + "-" +
                       std::to_string(i));
    }
    return keys;
}

// ------------------------------------------------- 1. ChainingHashMap
static void testChaining(std::mt19937_64& rng) {
    ChainingHashMap map;
    std::unordered_map<std::string, int> ref;

    const std::vector<std::string> keys = genKeys(rng, 4000);
    for (std::size_t i = 0; i < keys.size(); ++i) {
        const int v = static_cast<int>(i % 977);
        map.put(keys[i], v);
        ref[keys[i]] = v;
    }
    CHECK_EQ(map.size(), ref.size());

    // every key reads back, including the ones that were overwritten
    bool allOk = true;
    for (std::size_t i = 0; i < keys.size(); ++i) {
        int got = -1;
        if (!map.get(keys[i], got) || got != ref[keys[i]]) allOk = false;
    }
    CHECK(allOk);

    // duplicate-key update must not grow the table
    const std::size_t before = map.size();
    map.put(keys[0], 12345);
    CHECK_EQ(map.size(), before);
    int updated = 0;
    CHECK(map.get(keys[0], updated));
    CHECK_EQ(updated, 12345);

    // out of range: a key that was never inserted
    int miss = 0;
    CHECK(!map.get("no-such-key", miss));

    // remove every third key, then verify the survivors
    std::size_t removed = 0;
    for (std::size_t i = 0; i < keys.size(); i += 3) {
        CHECK(map.remove(keys[i]));
        ref.erase(keys[i]);
        ++removed;
    }
    CHECK(removed > 0);
    CHECK_EQ(map.size(), ref.size());
    bool survivorsOk = true;
    for (std::size_t i = 0; i < keys.size(); ++i) {
        int got = -1;
        const bool present = map.get(keys[i], got);
        const bool want = ref.find(keys[i]) != ref.end();
        if (present != want) survivorsOk = false;
        if (present && got != ref[keys[i]]) survivorsOk = false;
    }
    CHECK(survivorsOk);
    // removing twice must report false the second time
    CHECK(!map.remove(keys[0]));

    // empty table
    ChainingHashMap emptyMap;
    CHECK_EQ(emptyMap.size(), static_cast<std::size_t>(0));
    int nothing = 0;
    CHECK(!emptyMap.get("x", nothing));
    CHECK(!emptyMap.remove("x"));

    // single element
    ChainingHashMap one;
    one.put("only", 7);
    int oneVal = 0;
    CHECK(one.get("only", oneVal));
    CHECK_EQ(oneVal, 7);
    CHECK(one.remove("only"));
    CHECK_EQ(one.size(), static_cast<std::size_t>(0));
    CHECK(!one.get("only", oneVal));

    // all values equal: the table must stay consistent
    ChainingHashMap flat;
    for (int i = 0; i < 500; ++i) flat.put("k" + std::to_string(i), 42);
    bool flatOk = true;
    for (int i = 0; i < 500; ++i) {
        int got = 0;
        if (!flat.get("k" + std::to_string(i), got) || got != 42) flatOk = false;
    }
    CHECK(flatOk);
}

// ---------------------------------------------- 2. LinearProbingMap
static void testLinearProbing(std::mt19937_64& rng) {
    LinearProbingMap map;
    std::unordered_map<std::string, int> ref;

    const std::vector<std::string> keys = genKeys(rng, 4000);
    for (std::size_t i = 0; i < keys.size(); ++i) {
        const int v = static_cast<int>(i % 991);
        map.put(keys[i], v);
        ref[keys[i]] = v;
    }
    CHECK_EQ(map.size(), ref.size());
    bool allOk = true;
    for (std::size_t i = 0; i < keys.size(); ++i) {
        int got = -1;
        if (!map.get(keys[i], got) || got != ref[keys[i]]) allOk = false;
    }
    CHECK(allOk);

    // duplicate keys
    const std::size_t before = map.size();
    map.put(keys[0], -1);
    CHECK_EQ(map.size(), before);

    // the tombstone trap: after a delete, keys behind the hole must still be
    // reachable.  Delete in insertion order so every probe chain is stressed.
    std::size_t half = keys.size() / 2;
    for (std::size_t i = 0; i < half; ++i) {
        CHECK(map.remove(keys[i]));
        ref.erase(keys[i]);
    }
    CHECK_EQ(map.size(), ref.size());
    bool afterDelete = true;
    for (std::size_t i = 0; i < keys.size(); ++i) {
        int got = -1;
        const bool present = map.get(keys[i], got);
        const bool want = ref.find(keys[i]) != ref.end();
        if (present != want) afterDelete = false;
        if (present && got != ref[keys[i]]) afterDelete = false;
    }
    CHECK(afterDelete);

    // reinsert over the tombstones and delete again -- churn the table
    for (std::size_t i = 0; i < half; ++i) {
        map.put(keys[i], static_cast<int>(i));
        ref[keys[i]] = static_cast<int>(i);
    }
    CHECK_EQ(map.size(), ref.size());
    bool churnOk = true;
    for (std::size_t i = 0; i < keys.size(); ++i) {
        int got = -1;
        if (!map.get(keys[i], got) || got != ref[keys[i]]) churnOk = false;
    }
    CHECK(churnOk);

    // empty / single / out of range
    LinearProbingMap emptyMap;
    int nothing = 0;
    CHECK(!emptyMap.get("x", nothing));
    CHECK(!emptyMap.remove("x"));
    CHECK_EQ(emptyMap.size(), static_cast<std::size_t>(0));

    LinearProbingMap one;
    one.put("only", 5);
    int oneVal = 0;
    CHECK(one.get("only", oneVal));
    CHECK_EQ(oneVal, 5);
    CHECK(one.remove("only"));
    CHECK(!one.get("only", oneVal));
    int again = 0;
    CHECK(!one.get("only", again));

    // all-equal values, heavy collisions by construction
    LinearProbingMap flat;
    for (int i = 0; i < 400; ++i) flat.put("f" + std::to_string(i), 9);
    bool flatOk = true;
    for (int i = 0; i < 400; ++i) {
        int got = 0;
        if (!flat.get("f" + std::to_string(i), got) || got != 9) flatOk = false;
    }
    CHECK(flatOk);
}

// ------------------------------------------------- 3. ArrayHashMap
static void testArrayHashMap(std::mt19937_64& rng) {
    ArrayHashMap map;
    std::unordered_map<std::string, int> ref;

    const std::vector<std::string> keys = genKeys(rng, 2000);
    for (std::size_t i = 0; i < keys.size(); ++i) {
        map.put(keys[i], static_cast<int>(i));
        ref[keys[i]] = static_cast<int>(i);
    }
    CHECK_EQ(map.size(), ref.size());

    bool allOk = true;
    for (std::size_t i = 0; i < keys.size(); ++i) {
        int got = -1;
        if (!map.get(keys[i], got) || got != ref[keys[i]]) allOk = false;
    }
    CHECK(allOk);

    // randomKey must never return a key that is absent, and it must reach
    // every key (the swap-fill keeps entries_ compact)
    std::mt19937_64 pick(7);
    std::unordered_map<std::string, int> seen;
    for (int i = 0; i < 40000; ++i) {
        const std::string& k = map.randomKey(pick);
        if (ref.find(k) == ref.end()) {
            report(false, "randomKey returned an absent key");
            break;
        }
        ++seen[k];
    }
    CHECK_EQ(seen.size(), ref.size());

    // remove is where the swap-fill can corrupt the index
    std::size_t removed = 0;
    for (std::size_t i = 0; i < keys.size(); i += 2) {
        CHECK(map.remove(keys[i]));
        ref.erase(keys[i]);
        ++removed;
    }
    CHECK(removed > 0);
    CHECK_EQ(map.size(), ref.size());
    bool afterRemove = true;
    for (std::size_t i = 0; i < keys.size(); ++i) {
        int got = -1;
        const bool present = map.get(keys[i], got);
        const bool want = ref.find(keys[i]) != ref.end();
        if (present != want) afterRemove = false;
        if (present && got != ref[keys[i]]) afterRemove = false;
    }
    CHECK(afterRemove);

    // empty
    ArrayHashMap emptyMap;
    int nothing = 0;
    CHECK(!emptyMap.get("x", nothing));
    CHECK(!emptyMap.remove("x"));
    CHECK_EQ(emptyMap.size(), static_cast<std::size_t>(0));

    // single element: remove on the only entry (pos == last, no swap)
    ArrayHashMap one;
    one.put("only", 3);
    CHECK(one.remove("only"));
    CHECK_EQ(one.size(), static_cast<std::size_t>(0));
    int oneVal = 0;
    CHECK(!one.get("only", oneVal));

    // duplicate key update
    ArrayHashMap dup;
    dup.put("a", 1);
    dup.put("a", 2);
    CHECK_EQ(dup.size(), static_cast<std::size_t>(1));
    int dupVal = 0;
    CHECK(dup.get("a", dupVal));
    CHECK_EQ(dupVal, 2);
}

// ------------------------------------------------- 4. ConsistentHash
static void testConsistentHash() {
    ConsistentHash ring(200);
    CHECK_EQ(ring.ringSize(), static_cast<std::size_t>(0));
    // out of range: an empty ring has no node to hand back
    CHECK_EQ(ring.getNode("anything"), std::string());

    const std::vector<std::string> nodes = {"node-A", "node-B", "node-C"};
    for (const std::string& n : nodes) ring.addNode(n);
    CHECK_EQ(ring.ringSize(), nodes.size() * 200);

    std::vector<std::string> keys;
    for (int i = 0; i < 10000; ++i) keys.push_back("user-" + std::to_string(i));

    std::map<std::string, int> dist;
    std::vector<std::string> before;
    for (const std::string& k : keys) {
        const std::string owner = ring.getNode(k);
        CHECK(!owner.empty());
        ++dist[owner];
        before.push_back(owner);
    }
    CHECK_EQ(dist.size(), nodes.size());
    // every physical node must own roughly a third.  A weak hash breaks this:
    // with a bare FNV-1a (no avalanche) the split was 4900 / 3600 / 1500.
    bool spread = true;
    for (const std::pair<const std::string, int>& kv : dist) {
        if (kv.second < 2800 || kv.second > 3900) spread = false;
    }
    CHECK(spread);

    // determinism: the same key always maps to the same node
    bool stable = true;
    for (std::size_t i = 0; i < keys.size(); ++i) {
        if (ring.getNode(keys[i]) != before[i]) stable = false;
    }
    CHECK(stable);

    // scaling out: measure how many keys move when a 4th node joins
    ring.addNode("node-D");
    CHECK_EQ(ring.ringSize(), static_cast<std::size_t>(4 * 200));
    std::size_t moved = 0;
    for (std::size_t i = 0; i < keys.size(); ++i) {
        if (ring.getNode(keys[i]) != before[i]) ++moved;
    }
    std::cout << "       [consistent] 10000 keys / 3 nodes -> "
              << dist["node-A"] << " " << dist["node-B"] << " " << dist["node-C"]
              << " ; add a 4th node moves " << moved << " keys ("
              << (moved * 100.0 / static_cast<double>(keys.size())) << "%)\n";
    CHECK(moved > 0);
    CHECK(moved < keys.size() / 2);   // far below the ~75% that modulo hashing moves

    // scaling in: removing the new node restores the original mapping exactly
    ring.removeNode("node-D");
    CHECK_EQ(ring.ringSize(), nodes.size() * 200);
    std::size_t restored = 0;
    for (std::size_t i = 0; i < keys.size(); ++i) {
        if (ring.getNode(keys[i]) == before[i]) ++restored;
    }
    CHECK_EQ(restored, keys.size());

    // Modulo hashing on the same key set, for the contrast the post draws.
    // Old owner is nodes[h % 3], new owner is nodes4[h % 4]; a key moves
    // unless h % 3 == h % 4, which over one period of 12 happens 3 times.
    // So the expected migration is 1 - 3/12 = 3/4, i.e. about 75%.
    const std::vector<std::string> nodes4 = {"node-A", "node-B", "node-C",
                                            "node-D"};
    std::size_t modMoved = 0;
    for (const std::string& k : keys) {
        const std::size_t h = fnv1a(k);
        if (nodes[h % 3] != nodes4[h % 4]) ++modMoved;
    }
    std::cout << "       [consistent] plain modulo 3 -> 4 moves " << modMoved
              << " keys (" << (modMoved * 100.0 / static_cast<double>(keys.size()))
              << "%), consistent hashing moved " << moved << " keys ("
              << (moved * 100.0 / static_cast<double>(keys.size())) << "%)\n";
    CHECK(modMoved > 6 * keys.size() / 10);   // ~75%, not the ~25% of the ring
    CHECK(moved < modMoved / 2);
}

// ------------------------------------------------- 5. MinPQ
static void testMinPQ(std::mt19937_64& rng) {
    MinPQ pq;
    std::priority_queue<int, std::vector<int>, std::greater<int>> ref;
    CHECK(pq.empty());

    for (int i = 0; i < 5000; ++i) {
        const int v = static_cast<int>(rng() % 2001) - 1000;  // includes negatives
        pq.push(v);
        ref.push(v);
    }
    CHECK_EQ(pq.size(), static_cast<std::size_t>(5000));
    CHECK_EQ(pq.top(), ref.top());

    bool orderOk = true;
    while (!ref.empty()) {
        if (pq.top() != ref.top()) orderOk = false;
        if (pq.pop() != ref.top()) orderOk = false;
        ref.pop();
    }
    CHECK(orderOk);
    CHECK(pq.empty());

    // single element
    MinPQ one;
    one.push(7);
    CHECK_EQ(one.top(), 7);
    CHECK_EQ(one.pop(), 7);
    CHECK(one.empty());

    // all equal
    MinPQ flat;
    for (int i = 0; i < 200; ++i) flat.push(5);
    bool flatOk = true;
    for (int i = 0; i < 200; ++i) {
        if (flat.pop() != 5) flatOk = false;
    }
    CHECK(flatOk && flat.empty());

    // descending / ascending insertion order
    MinPQ desc;
    for (int i = 100; i > 0; --i) desc.push(i);
    bool descOk = true;
    for (int i = 1; i <= 100; ++i) {
        if (desc.pop() != i) descOk = false;
    }
    CHECK(descOk);

    MinPQ asc;
    for (int i = 1; i <= 100; ++i) asc.push(i);
    bool ascOk = true;
    for (int i = 1; i <= 100; ++i) {
        if (asc.pop() != i) ascOk = false;
    }
    CHECK(ascOk);
}

// ------------------------------------------------- 6. heap sort + build
static void testHeapSort(std::mt19937_64& rng) {
    // boundary shapes named in the post
    std::vector<std::vector<int>> cases;
    cases.push_back({});                                   // empty
    cases.push_back({1});                                  // single
    cases.push_back({2, 1});
    cases.push_back(std::vector<int>(50, 7));              // all equal
    cases.push_back({-5, -3, -9, -1, -7});                 // all negative
    cases.push_back({1, 2, 3, 4, 5, 6, 7, 8});             // already sorted
    cases.push_back({8, 7, 6, 5, 4, 3, 2, 1});             // reverse sorted
    for (int t = 0; t < 60; ++t) {
        std::vector<int> v;
        const std::size_t n = static_cast<std::size_t>(rng() % 40);
        for (std::size_t i = 0; i < n; ++i) {
            v.push_back(static_cast<int>(rng() % 21) - 10);  // many duplicates
        }
        cases.push_back(v);
    }

    bool allSorted = true;
    for (std::vector<int>& v : cases) {
        std::vector<int> want = v;
        std::sort(want.begin(), want.end());
        long long cmps = 0;
        heapSort(v, cmps);
        if (v != want) allSorted = false;
    }
    CHECK(allSorted);

    // in-place buildHeapFloyd must leave a valid max-heap
    bool heapOk = true;
    for (int t = 0; t < 60; ++t) {
        std::vector<int> v;
        const std::size_t n = 1 + static_cast<std::size_t>(rng() % 40);
        for (std::size_t i = 0; i < n; ++i) v.push_back(static_cast<int>(rng() % 51));
        long long cmps = 0;
        buildHeapFloyd(v, cmps);
        for (std::size_t i = 1; i < v.size(); ++i) {
            if (v[(i - 1) / 2] < v[i]) heapOk = false;
        }
    }
    CHECK(heapOk);

    // Floyd build is O(n): comparisons must stay under 2n
    bool floydBound = true;
    bool floydBeatsSwim = true;
    for (int t = 0; t < 40; ++t) {
        const std::size_t n = 1 + static_cast<std::size_t>(rng() % 3000);
        std::vector<int> v;
        for (std::size_t i = 0; i < n; ++i) v.push_back(static_cast<int>(rng() % 100000));
        std::vector<int> a = v;
        std::vector<int> b = v;
        long long cf = 0;
        long long cs = 0;
        buildHeapFloyd(a, cf);
        buildHeapBySwim(b, cs);
        if (cf > 2 * static_cast<long long>(n)) floydBound = false;
        if (cs <= cf) floydBeatsSwim = false;
    }
    CHECK(floydBound);
    CHECK(floydBeatsSwim);

    // the headline measurement: n = 2^20, Floyd vs swim
    const std::size_t n = static_cast<std::size_t>(1) << 20;
    std::vector<int> big(n);
    for (std::size_t i = 0; i < n; ++i) big[i] = static_cast<int>(rng() % 1000000);
    std::vector<int> bigSwim = big;
    long long floyd = 0;
    long long swim = 0;
    buildHeapFloyd(big, floyd);
    buildHeapBySwim(bigSwim, swim);
    std::cout << "       [buildheap] n = 2^20 = " << n
              << " ; Floyd build comparisons = " << floyd << " ("
              << (static_cast<double>(floyd) / static_cast<double>(n))
              << "n) ; swim build = " << swim << " ("
              << (static_cast<double>(swim) / static_cast<double>(n)) << "n)\n";
    CHECK(floyd < 2 * static_cast<long long>(n));
    CHECK(swim > floyd);

    // and the sort itself on that size
    std::vector<int> toSort = big;
    long long sortCmps = 0;
    heapSort(toSort, sortCmps);
    CHECK(std::is_sorted(toSort.begin(), toSort.end()));
    CHECK_EQ(toSort.front(), *std::min_element(big.begin(), big.end()));
}

// ------------------------------------------------- 7. TrieMap
static void testTrie() {
    TrieMap trie;
    std::set<std::string> keys;

    // the exact example the post prints
    const std::vector<std::string> words = {"that", "the", "them", "apple"};
    for (const std::string& w : words) {
        trie.insert(w);
        keys.insert(w);
    }
    CHECK(trie.search("that"));
    CHECK(trie.search("the"));
    CHECK(trie.search("them"));
    CHECK(trie.search("apple"));
    // "th" is a real path but not a key: search false, startsWith true
    CHECK(!trie.search("th"));
    CHECK(trie.startsWith("th"));
    CHECK(trie.startsWith("tha"));
    CHECK(!trie.startsWith("thz"));
    CHECK(!trie.search("thz"));
    CHECK(!trie.search("app"));
    CHECK(trie.startsWith("app"));
    CHECK(!trie.search("applex"));
    CHECK(!trie.startsWith("applex"));
    CHECK(!trie.startsWith("z"));

    // duplicate insert must be idempotent
    trie.insert("the");
    CHECK(trie.search("the"));
    CHECK_EQ(keys.size(), static_cast<std::size_t>(4));

    // empty string is a legal key: the root becomes an end node
    trie.insert("");
    CHECK(trie.search(""));
    CHECK(trie.startsWith(""));
    trie.insert("a");
    CHECK(trie.search("a"));

    // exhaustive cross-check against the reference for a bigger alphabet soup
    std::mt19937_64 rng(20261116);
    TrieMap big;
    std::set<std::string> bigKeys;
    for (int i = 0; i < 2000; ++i) {
        std::string w;
        const std::size_t len = 1 + static_cast<std::size_t>(rng() % 8);
        for (std::size_t j = 0; j < len; ++j) {
            w.push_back(static_cast<char>('a' + static_cast<int>(rng() % 3)));
        }
        big.insert(w);
        bigKeys.insert(w);
    }
    bool searchOk = true;
    for (int i = 0; i < 3000; ++i) {
        std::string w;
        const std::size_t len = static_cast<std::size_t>(rng() % 6);
        for (std::size_t j = 0; j < len; ++j) {
            w.push_back(static_cast<char>('a' + static_cast<int>(rng() % 4)));
        }
        if (big.search(w) != (bigKeys.count(w) == 1)) searchOk = false;
        bool wantPrefix = false;
        for (const std::string& k : bigKeys) {
            if (k.size() >= w.size() && k.compare(0, w.size(), w) == 0) {
                wantPrefix = true;
                break;
            }
        }
        if (big.startsWith(w) != wantPrefix) searchOk = false;
    }
    CHECK(searchOk);
}

// ------------------------------------------------- 8. segment trees
static long long bruteSum(const std::vector<long long>& a, int l, int r) {
    long long s = 0;
    for (int i = l; i <= r; ++i) s += a[static_cast<std::size_t>(i)];
    return s;
}

static long long bruteMax(const std::vector<long long>& a, int l, int r) {
    long long m = a[static_cast<std::size_t>(l)];
    for (int i = l + 1; i <= r; ++i) {
        m = std::max(m, a[static_cast<std::size_t>(i)]);
    }
    return m;
}

static void testSegTree(std::mt19937_64& rng) {
    const std::function<long long(long long, long long)> add =
        [](long long a, long long b) { return a + b; };
    const std::function<long long(long long, long long)> maxf =
        [](long long a, long long b) { return a > b ? a : b; };
    const long long negInf = std::numeric_limits<long long>::min();

    // empty: constructing must be safe
    const std::vector<long long> none;
    SegTree emptyTree(none, add, 0);
    (void)emptyTree;

    // single element
    {
        const std::vector<long long> one = {42};
        SegTree t(one, add, 0);
        CHECK_EQ(t.query(0, 0), 42LL);
        t.update(0, -42);
        CHECK_EQ(t.query(0, 0), -42LL);
    }

    // all equal
    {
        const std::vector<long long> flat(64, 6);
        SegTree t(flat, add, 0);
        CHECK_EQ(t.query(0, 63), 64 * 6LL);
        CHECK_EQ(t.query(10, 20), 11 * 6LL);
    }

    // all negative with a max tree: this is the identity-element trap.  A max
    // tree built with identity 0 returns 0 for the disjoint branch, and
    // max(0, negative) = 0, so every all-negative range reads back 0.
    {
        const std::vector<long long> neg = {-5, -3, -9, -1, -7};
        SegTree t(neg, maxf, negInf);
        CHECK_EQ(t.query(0, 4), -1LL);
        CHECK_EQ(t.query(1, 2), -3LL);
        CHECK_EQ(t.query(4, 4), -7LL);
        SegTree sumNeg(neg, add, 0);
        CHECK_EQ(sumNeg.query(0, 4), -25LL);
        CHECK_EQ(sumNeg.query(2, 3), -10LL);
    }

    // randomized sweep over every (l, r) pair, both merges
    bool sumOk = true;
    bool maxOk = true;
    bool updateOk = true;
    for (int t = 0; t < 40; ++t) {
        const int n = 1 + static_cast<int>(rng() % 40);
        std::vector<long long> a;
        for (int i = 0; i < n; ++i) {
            a.push_back(static_cast<long long>(rng() % 201) - 100);
        }
        SegTree st(a, add, 0);
        SegTree mt(a, maxf, negInf);
        for (int l = 0; l < n; ++l) {
            for (int r = l; r < n; ++r) {
                if (st.query(l, r) != bruteSum(a, l, r)) sumOk = false;
                if (mt.query(l, r) != bruteMax(a, l, r)) maxOk = false;
            }
        }
        // interleave single-point updates with full re-checks
        for (int u = 0; u < 20; ++u) {
            const int idx = static_cast<int>(rng() % static_cast<std::size_t>(n));
            const long long val =
                static_cast<long long>(rng() % 201) - 100;
            a[static_cast<std::size_t>(idx)] = val;
            st.update(idx, val);
            mt.update(idx, val);
            for (int l = 0; l < n; ++l) {
                for (int r = l; r < n; ++r) {
                    if (st.query(l, r) != bruteSum(a, l, r)) updateOk = false;
                    if (mt.query(l, r) != bruteMax(a, l, r)) updateOk = false;
                }
            }
        }
    }
    CHECK(sumOk);
    CHECK(maxOk);
    CHECK(updateOk);
}

static void testLazySegTree(std::mt19937_64& rng) {
    // single element
    {
        const std::vector<long long> one = {5};
        LazySegTree t(one);
        CHECK_EQ(t.rangeSum(0, 0), 5LL);
        t.rangeAdd(0, 0, -3);
        CHECK_EQ(t.rangeSum(0, 0), 2LL);
    }
    // all equal + a full-range add
    {
        const std::vector<long long> flat(32, 4);
        LazySegTree t(flat);
        t.rangeAdd(0, 31, 6);
        CHECK_EQ(t.rangeSum(0, 31), 32 * 10LL);
        CHECK_EQ(t.rangeSum(7, 9), 3 * 10LL);
        t.rangeAdd(0, 31, -10);                 // 4 + 6 - 10 == 0 everywhere
        CHECK_EQ(t.rangeSum(0, 31), 0LL);
        t.rangeAdd(0, 31, 4);                   // put it back to 4 each
        CHECK_EQ(t.rangeSum(0, 31), 32 * 4LL);
    }
    // the lazy trap: many overlapping adds that are only pushed down when a
    // partial query forces it
    {
        const int n = 64;
        std::vector<long long> a(n, 0);
        LazySegTree t(a);
        for (int round = 0; round < 300; ++round) {
            const int l = static_cast<int>(rng() % static_cast<std::size_t>(n));
            const int r =
                l + static_cast<int>(rng() % static_cast<std::size_t>(n - l));
            const long long delta =
                static_cast<long long>(rng() % 41) - 20;   // may be negative
            t.rangeAdd(l, r, delta);
            for (int i = l; i <= r; ++i) a[static_cast<std::size_t>(i)] += delta;

            if (round % 7 == 0) {
                int ql = static_cast<int>(rng() % static_cast<std::size_t>(n));
                int qr = ql + static_cast<int>(rng() % static_cast<std::size_t>(n - ql));
                CHECK_EQ(t.rangeSum(ql, qr), bruteSum(a, ql, qr));
            }
        }
        bool full = true;
        for (int l = 0; l < n; ++l) {
            for (int r = l; r < n; ++r) {
                if (t.rangeSum(l, r) != bruteSum(a, l, r)) full = false;
            }
        }
        CHECK(full);
    }
}

// ------------------------------------------------- 9. Fenwick
static void testFenwick(std::mt19937_64& rng) {
    // single element
    {
        Fenwick f(1);
        CHECK_EQ(f.prefixSum(1), 0LL);
        f.add(1, 9);
        CHECK_EQ(f.prefixSum(1), 9LL);
        CHECK_EQ(f.rangeSum(1, 1), 9LL);
        f.add(1, -9);
        CHECK_EQ(f.prefixSum(1), 0LL);
    }
    // exhaustive: every n up to 40, every i, against brute force
    bool prefixOk = true;
    bool rangeOk = true;
    for (std::size_t n = 1; n <= 40; ++n) {
        std::vector<long long> a(n + 1, 0);   // 1-based
        Fenwick f(n);
        for (int step = 0; step < 60; ++step) {
            const std::size_t i = 1 + rng() % n;
            const long long delta = static_cast<long long>(rng() % 41) - 20;
            a[i] += delta;
            f.add(i, delta);
            for (std::size_t k = 1; k <= n; ++k) {
                long long want = 0;
                for (std::size_t j = 1; j <= k; ++j) want += a[j];
                if (f.prefixSum(k) != want) prefixOk = false;
            }
            for (std::size_t l = 1; l <= n; ++l) {
                for (std::size_t r = l; r <= n; ++r) {
                    long long want = 0;
                    for (std::size_t j = l; j <= r; ++j) want += a[j];
                    if (f.rangeSum(l, r) != want) rangeOk = false;
                }
            }
        }
    }
    CHECK(prefixOk);
    CHECK(rangeOk);

    // all-equal / all-zero / all-negative
    {
        Fenwick f(16);
        for (std::size_t i = 1; i <= 16; ++i) f.add(i, 3);
        CHECK_EQ(f.prefixSum(16), 48LL);
        CHECK_EQ(f.rangeSum(1, 16), 48LL);
        for (std::size_t i = 1; i <= 16; ++i) f.add(i, -5);
        CHECK_EQ(f.prefixSum(16), -32LL);
        CHECK_EQ(f.rangeSum(4, 4), -2LL);
        for (std::size_t i = 1; i <= 16; ++i) f.add(i, 2);
        CHECK_EQ(f.prefixSum(16), 0LL);
    }
    // lowbit must agree with the two spellings and with the definition
    CHECK_EQ(Fenwick::lowbit(0), static_cast<std::size_t>(0));
    CHECK_EQ(Fenwick::lowbit(1), static_cast<std::size_t>(1));
    CHECK_EQ(Fenwick::lowbit(6), static_cast<std::size_t>(2));
    CHECK_EQ(Fenwick::lowbit(12), static_cast<std::size_t>(4));
    CHECK_EQ(Fenwick::lowbit(1024), static_cast<std::size_t>(1024));
    bool lowbitOk = true;
    for (std::size_t i = 1; i <= 4096; ++i) {
        if (Fenwick::lowbit(i) != (i & (~i + 1))) lowbitOk = false;
        if (Fenwick::lowbit(i) > i) lowbitOk = false;
        if (i % Fenwick::lowbit(i) != 0) lowbitOk = false;
    }
    CHECK(lowbitOk);

    // measured step counts: prefixSum(i) walks popcount(i) nodes, add(i) walks
    // until it passes n
    const std::size_t n = 1024;
    std::size_t maxPrefixSteps = 0;
    for (std::size_t i = 1; i <= n; ++i) {
        std::size_t steps = 0;
        for (std::size_t j = i; j > 0; j -= Fenwick::lowbit(j)) ++steps;
        maxPrefixSteps = std::max(maxPrefixSteps, steps);
    }
    std::size_t maxAddSteps = 0;
    for (std::size_t i = 1; i <= n; ++i) {
        std::size_t steps = 0;
        for (std::size_t j = i; j <= n; j += Fenwick::lowbit(j)) ++steps;
        maxAddSteps = std::max(maxAddSteps, steps);
    }
    std::cout << "       [bit] n = " << n << " ; max prefixSum steps = "
              << maxPrefixSteps << " ; max add steps = " << maxAddSteps
              << " ; log2(n) = 10\n";
    CHECK_EQ(maxPrefixSteps, static_cast<std::size_t>(10));   // popcount(1023)
    CHECK_EQ(maxAddSteps, static_cast<std::size_t>(11));      // 1,2,4,...,1024
}

// ------------------------------------------------- 10. SkipList
static void testSkipList(std::mt19937_64& rng) {
    // empty
    {
        SkipList sl;
        CHECK_EQ(sl.size(), static_cast<std::size_t>(0));
        CHECK(!sl.contains(1));
        CHECK(!sl.erase(1));
        sl.insert(1);
        CHECK(sl.contains(1));
        CHECK(sl.erase(1));
        CHECK(!sl.contains(1));
        CHECK_EQ(sl.size(), static_cast<std::size_t>(0));
    }
    // single element
    {
        SkipList sl;
        sl.insert(50);
        CHECK(sl.contains(50));
        CHECK(!sl.contains(49));
        CHECK(!sl.contains(51));
        sl.erase(50);
        CHECK(!sl.contains(50));
    }
    // all-equal inserts: the list must refuse duplicates
    {
        SkipList sl;
        for (int i = 0; i < 200; ++i) sl.insert(7);
        CHECK_EQ(sl.size(), static_cast<std::size_t>(1));
        CHECK(sl.contains(7));
        CHECK(sl.erase(7));
        CHECK_EQ(sl.size(), static_cast<std::size_t>(0));
    }
    // randomized cross-check against std::set
    {
        SkipList sl;
        std::set<int> ref;
        for (int i = 0; i < 20000; ++i) {
            const int v = static_cast<int>(rng() % 3000);
            switch (rng() % 3) {
                case 0:
                    sl.insert(v);
                    ref.insert(v);
                    break;
                case 1:
                    CHECK_EQ(sl.contains(v), ref.count(v) == 1);
                    break;
                default:
                    CHECK_EQ(sl.erase(v), ref.erase(v) == 1);
                    break;
            }
        }
        CHECK_EQ(sl.size(), ref.size());
        bool agree = true;
        for (int v = 0; v < 3000; ++v) {
            if (sl.contains(v) != (ref.count(v) == 1)) agree = false;
        }
        CHECK(agree);
        // erase everything; the level must fall back to 1
        for (const int v : ref) {
            CHECK(sl.erase(v));
        }
        CHECK_EQ(sl.size(), static_cast<std::size_t>(0));
        CHECK_EQ(sl.level(), 1);
    }
    // the headline measurement: 65536 inserts, average lookup cost
    {
        SkipList sl;
        std::set<int> ref;
        const int n = 65536;
        long long insertSteps = 0;
        for (int i = 0; i < n; ++i) {
            const int v = static_cast<int>(rng() % 10000000);
            sl.insert(v);
            ref.insert(v);
            insertSteps += sl.lastSteps();
        }
        CHECK_EQ(sl.size(), ref.size());
        long long lookupSteps = 0;
        int hits = 0;
        const int probes = 20000;
        for (int i = 0; i < probes; ++i) {
            const int v = static_cast<int>(rng() % 10000000);
            if (sl.contains(v)) ++hits;
            lookupSteps += sl.lastSteps();
        }
        std::cout << "       [skiplist] n = " << sl.size()
                  << " ; level = " << sl.level()
                  << " ; avg insert steps = "
                  << (static_cast<double>(insertSteps) / n)
                  << " ; avg lookup steps = "
                  << (static_cast<double>(lookupSteps) / probes)
                  << " ; hits = " << hits << "/" << probes << "\n";
        // expected O(log n): the move count must be far below n
        CHECK(insertSteps / n < 100);
        CHECK(lookupSteps / probes < 100);
        CHECK(sl.level() > 1);
    }
}

// ------------------------------------------------- 11. measured tables
static void measureRehash() {
    // the O(1) amortised claim: 2^20 inserts must move well under 1.5 n
    ChainingHashMap map;
    const std::size_t n = static_cast<std::size_t>(1) << 20;
    for (std::size_t i = 0; i < n; ++i) {
        map.put("k" + std::to_string(i), static_cast<int>(i));
    }
    const long long ops = map.rehashOps();
    std::cout << "       [rehash] n = " << n << " ; rehashOps = " << ops
              << " (" << (static_cast<double>(ops) / static_cast<double>(n))
              << "n) ; bound 1.5n = " << (1.5 * static_cast<double>(n))
              << " ; final capacity = " << map.capacity() << "\n";
    CHECK_EQ(map.size(), n);
    // The derivation in the post gives 1.5n.  The real count is 1.5n + 12:
    // the trigger is `size_ * 4 > table_.size() * 3`, so each resize fires one
    // element later than 0.75*cap, and there are 12 resizes here.  Assert a
    // tight band so the check still fails loudly if the accounting regresses.
    CHECK(static_cast<double>(ops) > 1.4 * static_cast<double>(n));
    CHECK(static_cast<double>(ops) <= 1.5 * static_cast<double>(n) + 64.0);
    CHECK_EQ(ops - static_cast<long long>(n + n / 2), 12LL);
}

int run_all_tests() {
    std::mt19937_64 rng(20261116);
    std::cout << "       running C++ checks\n";
    testChaining(rng);
    testLinearProbing(rng);
    testArrayHashMap(rng);
    testConsistentHash();
    testMinPQ(rng);
    testHeapSort(rng);
    testTrie();
    testSegTree(rng);
    testLazySegTree(rng);
    testFenwick(rng);
    testSkipList(rng);
    measureRehash();
    std::cout << "       " << g_checks << " assertions, " << g_fail
              << " failures\n";
    return g_fail == 0 ? 0 : 1;
}
