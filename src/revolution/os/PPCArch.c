#include <types.h>

#define HID0_SPD 0x200
#define HID4_H4A 0x80000000

void OSReport(const char* msg, ...);

typedef union FpscrUnion {
    f64 f;
    struct {
        u32 fpscr_pad;
        u32 fpscr;
    } u;
} FpscrUnion;

asm u32 PPCMfmsr(void) {
    nofralloc
    mfmsr r3
    blr
}

asm void PPCMtmsr(register u32 val) {
    nofralloc
    mtmsr val
    blr
}

asm u32 PPCMfhid0(void) {
    nofralloc
    mfspr r3, HID0
    blr
}

asm void PPCMthid0(register u32 val) {
    nofralloc
    mtspr HID0, val
    blr
}

asm u32 PPCMfl2cr(void) {
    nofralloc
    mfspr r3, L2CR
    blr
}

asm void PPCMtl2cr(register u32 val) {
    nofralloc
    mtspr L2CR, val
    blr
}

asm void PPCMtdec(register u32 val) {
    nofralloc
    mtdec val
    blr
}

asm void PPCSync(void) {
    nofralloc
    sc
    blr
}

asm void PPCHalt(void) {
    nofralloc
    sync
loop:
    nop
    li r3, 0
    nop
    b loop
}

asm void PPCMtmmcr0(register u32 val) {
    nofralloc
    mtspr MMCR0, val
    blr
}

asm void PPCMtmmcr1(register u32 val) {
    nofralloc
    mtspr MMCR1, val
    blr
}

asm void PPCMtpmc1(register u32 val) {
    nofralloc
    mtspr PMC1, val
    blr
}

asm void PPCMtpmc2(register u32 val) {
    nofralloc
    mtspr PMC2, val
    blr
}

asm void PPCMtpmc3(register u32 val) {
    nofralloc
    mtspr PMC3, val
    blr
}

asm void PPCMtpmc4(register u32 val) {
    nofralloc
    mtspr PMC4, val
    blr
}

u32 PPCMffpscr(void) {
    FpscrUnion m;

    asm {
        mffs fp31
        stfd fp31, m.f
    }

    return m.u.fpscr;
}

void PPCMtfpscr(register u32 val) {
    FpscrUnion m;

    asm {
        li r4, 0
        stw val, m.u.fpscr
        stw r4, m.u.fpscr_pad
        lfd fp31, m.f
        mtfsf 0xff, fp31
    }
}

asm u32 PPCMfhid2(void) {
    nofralloc
    mfspr r3, 920
    blr
}

asm void PPCMthid2(register u32 val) {
    nofralloc
    mtspr 920, val
    blr
}

asm void PPCMtwpar(register u32 val) {
    nofralloc
    mtspr WPAR, val
    blr
}

void PPCDisableSpeculation(void) {
    PPCMthid0(PPCMfhid0() | HID0_SPD);
}

asm void PPCSetFpNonIEEEMode(void) {
    nofralloc
    mtfsb1 29
    blr
}

void PPCMthid4(register u32 hid4) {
    if (hid4 & HID4_H4A) {
        asm { mtspr 1011, hid4 }
    } else {
        OSReport("H4A should not be cleared because of Broadway errata.\n");
        hid4 |= HID4_H4A;
        asm { mtspr 1011, hid4 }
    }
}
