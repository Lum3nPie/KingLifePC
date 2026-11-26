#include <game/WCThread.h>
#include <game/WCMemory.h>

WCThread::WCThread() : mOwnThread(NULL), mArg(NULL), mStack(NULL), mThread(NULL), mName("WCThread") {
    Destroy();
}

bool WCThread::Create(OSThreadStartFunction func, void* arg, void* stack, u32 stackSize, s32 priority,
                      const char* name) {
    Destroy();
    mOwnThread = new (1) OSThread;
    mArg = arg;
    if (stack == NULL) {
        stack = new (32, 1) u8[stackSize];
        mStack = stack;
    }
    OSCreateThread(mOwnThread, func, this, (u8*)stack + stackSize, stackSize, priority, 1);
    mName = name;
    mThread = mOwnThread;
    return true;
}

void WCThread::Resume() {
    if (mOwnThread != NULL) {
        OSResumeThread(mOwnThread);
    }
}

void WCThread::Cancel() {
    if (mOwnThread != NULL) {
        OSCancelThread(mOwnThread);
    }
}

bool WCThread::IsTerminated() {
    if (mOwnThread == NULL) {
        return false;
    }
    return OSIsThreadTerminated(mOwnThread);
}

void WCThread::Destroy() {
    if (mOwnThread != NULL) {
        OSCancelThread(mOwnThread);
        if (mOwnThread != NULL) {
            delete mOwnThread;
            mOwnThread = NULL;
        }
    }
    if (mStack != NULL) {
        delete[] (u8*)mStack;
        mStack = NULL;
    }
}

void WCThread::Attach(OSThread* thread, const char* name) {
    mThread = thread;
    mName = name;
}
