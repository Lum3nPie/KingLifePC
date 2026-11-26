#ifndef GAME_WCTHREAD_H
#define GAME_WCTHREAD_H

#include <revolution/os.h>

class WCThread {
public:
    WCThread();

    bool Create(OSThreadStartFunction func, void* arg, void* stack, u32 stackSize, s32 priority, const char* name);
    void Resume();
    void Cancel();
    bool IsTerminated();
    void Destroy();
    void Attach(OSThread* thread, const char* name);

private:
    OSThread* mOwnThread; // 0x0
    void* mArg;           // 0x4
    void* mStack;         // 0x8
    OSThread* mThread;    // 0xC
    const char* mName;    // 0x10
};

#endif
