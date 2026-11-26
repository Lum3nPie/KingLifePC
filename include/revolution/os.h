#ifndef REVOLUTION_OS_H
#define REVOLUTION_OS_H

#include <types.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct OSThread {
    u8 data[0x318];
} OSThread;

typedef void* (*OSThreadStartFunction)(void* arg);

OSThread* OSGetCurrentThread(void);
BOOL OSIsThreadTerminated(OSThread* thread);
BOOL OSCreateThread(OSThread* thread, OSThreadStartFunction func, void* param, void* stack, u32 stackSize,
                    s32 priority, u16 attr);
s32 OSResumeThread(OSThread* thread);
void OSCancelThread(OSThread* thread);
void OSReport(const char* msg, ...);

#ifdef __cplusplus
}
#endif

#endif
