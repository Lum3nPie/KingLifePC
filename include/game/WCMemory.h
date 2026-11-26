#ifndef GAME_WCMEMORY_H
#define GAME_WCMEMORY_H

#include <types.h>

// Game allocators (0x800920C4 area). The int selects the heap: 1 = MEM2, otherwise MEM1 (to be confirmed).
void* operator new(size_t size, int heap);
void* operator new[](size_t size, int align, int heap);
void operator delete(void* p);
void operator delete[](void* p);

#endif
