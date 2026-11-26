#include <revolution/os.h>
#include <game/WCThread.h>
#include <msl/string>

extern "C" {
s32 SCCheckStatus(void);
void SCInit(void);
OSThread* fn_8010333C(void);
void fn_800918C8(int);
void fn_801CDAAC(int);
void fn_80092084(void);
void fn_801BB470(void);
void fn_801FE85C(void);
void fn_801FE8A0(void);
void* fn_8004328C(void);
void fn_80043298(void*);
void fn_800432D4(void*, int);
void fn_80032AD4(void*, std::string*, std::string*);
void fn_80032CF0(void*);
void fn_80032C90(void*);
extern int lbl_8039DC08;
extern u8 lbl_802B1B78[];
}

static inline void OSInitFastCast(void) {
    asm {
        li r3, 4
        oris r3, r3, 4
        mtspr 914, r3
        li r3, 5
        oris r3, r3, 5
        mtspr 915, r3
        li r3, 6
        oris r3, r3, 6
        mtspr 916, r3
        li r3, 7
        oris r3, r3, 7
        mtspr 917, r3
    }
}

static WCThread sMainThread;
static WCThread sGXThread;

void main(void) {
    sMainThread.Attach(OSGetCurrentThread(), "main");
    lbl_8039DC08 = 1;
    fn_800918C8(0);
    fn_801CDAAC(1);
    fn_80092084();
    fn_801BB470();
    SCInit();
    while (SCCheckStatus() != 0) {
    }
    OSInitFastCast();
    sGXThread.Attach(fn_8010333C(), "GX");
    fn_801FE85C();

    {
        std::string settings("settings_master.xml");
        std::string other;
        fn_80043298(fn_8004328C());
        fn_800432D4(fn_8004328C(), 2);
        fn_80032AD4(lbl_802B1B78, &settings, &other);
        fn_80032CF0(lbl_802B1B78);
        fn_80032C90(lbl_802B1B78);
    }
    fn_801FE8A0();
}
