.intel_syntax noprefix
.section .text

/* Road Lamp Direction v1.0.0 — checked frame-queue hook installer. */

.equ DATA_API,           0x3008
.equ DATA_MAIN,          0x3010
.equ DATA_TRAMP,         0x3018
.equ DATA_ENABLED,       0x3030
.equ DATA_SIG,           0x3040

.equ TARGET_QUEUE,       0x585820
.equ CALLBACK_QUEUE,     0x7000
.equ SPAN_DECODER,       0x1280

.equ STR_HOOK,           0x2041
.equ STR_UNREADABLE,     0x2110
.equ STR_PROLOGUE,       0x2160
.equ STR_HOOK_FAIL,      0x21b0
.equ STR_READY,          0x2200

.global plugin_start
plugin_start:
    push rsi
    push rdi
    push rbx
    push r12
    sub rsp, 0x38

    lea rdi, [rip + plugin_start]
    and rdi, -0x10000
    mov rsi, qword ptr [rdi + DATA_API]
    test rsi, rsi
    je start_fail_silent
    cmp qword ptr [rsi + 0x50], 0
    je start_fail_silent
    cmp qword ptr [rsi + 0x60], 0
    je start_fail_silent
    cmp qword ptr [rdi + DATA_MAIN], 0
    je start_fail_silent

    mov byte ptr [rdi + DATA_ENABLED], 0

    mov rbx, qword ptr [rdi + DATA_MAIN]
    add rbx, TARGET_QUEUE
    mov rcx, rbx
    mov edx, 32
    call qword ptr [rsi + 0x60]
    test eax, eax
    je fail_unreadable

    mov rcx, rbx
    lea rax, [rdi + SPAN_DECODER]
    call rax
    test eax, eax
    je fail_prologue
    mov r12d, eax

    lea r11, [rdi + DATA_SIG]
    xor ecx, ecx
copy_signature:
    mov al, byte ptr [rbx + rcx]
    mov byte ptr [r11 + rcx], al
    inc ecx
    cmp ecx, r12d
    jb copy_signature

    mov rcx, rbx
    lea rdx, [rdi + CALLBACK_QUEUE]
    lea r8, [rdi + DATA_TRAMP]
    lea r9, [rdi + DATA_SIG]
    mov qword ptr [rsp + 0x20], r12
    lea rax, [rdi + STR_HOOK]
    mov qword ptr [rsp + 0x28], rax
    call qword ptr [rsi + 0x50]
    test eax, eax
    je fail_hook

    mov byte ptr [rdi + DATA_ENABLED], 1
    lea rcx, [rdi + STR_READY]
    call log_line
    xor eax, eax
    jmp start_return

fail_unreadable:
    lea rcx, [rdi + STR_UNREADABLE]
    jmp start_fail_log
fail_prologue:
    lea rcx, [rdi + STR_PROLOGUE]
    jmp start_fail_log
fail_hook:
    lea rcx, [rdi + STR_HOOK_FAIL]
start_fail_log:
    call log_line
start_fail_silent:
    mov eax, 1
start_return:
    add rsp, 0x38
    pop r12
    pop rbx
    pop rdi
    pop rsi
    ret

.global plugin_start_end
plugin_start_end:

log_line:
    mov rax, qword ptr [rsi + 0x38]
    test rax, rax
    je log_done
    jmp rax
log_done:
    ret

.global plugin_code_end
plugin_code_end:
