#ifndef MSL_MSL_COMMON_H
#define MSL_MSL_COMMON_H

// Shared declarations for the MSL C++ reconstruction (see include/msl/string).
// Layout and member structure follow TheLastStoryDecomp's reconstruction (CC0-1.0), adapted to the
// older MSL used by this game (allocator::allocate takes a hint and is a weak function).

typedef unsigned long __msl_size_t;

void* operator new(__msl_size_t size);
void operator delete(void* p);

struct _FILE_unk {
    unsigned char m00[0x50];
};

extern "C" _FILE_unk __files[];
extern "C" int fprintf(_FILE_unk* file, const char* format, ...);
extern "C" void abort();
extern "C" unsigned long strlen(const char* s);
extern "C" void* memmove(void* dst, const void* src, unsigned long n);
extern "C" void* memcpy(void* dst, const void* src, unsigned long n);

// MSL reports errors with fprintf(stderr, ...) + abort() when exceptions are off.
inline void __msl_error(const char* msg) {
    fprintf(&__files[2], msg);
    abort();
}

#endif
