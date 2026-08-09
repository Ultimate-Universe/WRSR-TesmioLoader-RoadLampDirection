.intel_syntax noprefix
.section .text

/*
 * Road Lamp Direction v1.0.0 — green-preview material filter.
 *
 * FUN_140585820 copies 0x30-byte staging records into the frame road queues.
 * Call it first, then inspect the copied records only while the exact custom
 * lamp descriptor is active.
 *
 * The decompiled road editor resolves ordinary roads through editor+0xF7A0. This
 * callback therefore compares against the six one-way materials owned by that
 * exact live road system and rewrites matching frame-local records to its
 * ordinary line material.  No road, shared material, texture, or staging
 * record is modified.
 */

.equ DATA_API,                 0x3008
.equ DATA_MAIN,                0x3010
.equ DATA_TRAMPOLINE,          0x3018
.equ DATA_ROADLAMP_BASE,       0x3028
.equ DATA_ENABLED,             0x3030
.equ DATA_ACTIVE_LOGGED,       0x3031
.equ DATA_CAND_A_LOGGED,       0x3032
.equ DATA_CAND_B_LOGGED,       0x3033
.equ DATA_REWRITE_LOGGED,      0x3034
.equ DATA_ACTIVE_SCANS,        0x3038
.equ DATA_REWRITE_COUNT,       0x303c

.equ ROADLAMP_EDITOR,          0x5050
.equ ROADLAMP_DESC,            0x5090
.equ EDITOR_ACTIVE,            0xd428
.equ EDITOR_ROAD_SYSTEM,       0xf7a0

.equ QUEUE_A_BEGIN,            0x997140
.equ QUEUE_A_END,              0x997148
.equ QUEUE_B_BEGIN,            0x997170
.equ QUEUE_B_END,              0x997178

.equ MAT_LINE,                 0x0b8
.equ MAT_ONEWAY_1,             0x0c0
.equ MAT_ONEWAY_2,             0x0c8
.equ MAT_ONEWAY_LANE_1,        0x0d0
.equ MAT_ONEWAY_LANE_2,        0x0d8
.equ MAT_ONEWAY_BP_1,          0x108
.equ MAT_ONEWAY_BP_2,          0x110
.equ MAT_LINE_BP,              0x190

.equ RECORD_SIZE,              0x30
.equ MAX_QUEUE_BYTES,          0x30000
.equ LOCAL_STACK_SIZE,         0x48
.equ RESOLVE_PLUGIN_BASE,      0x1710

.global callback_start
callback_start:
    push r15
    push r14
    push r13
    push r12
    push rsi
    push rdi
    push rbp
    push rbx
    sub rsp, LOCAL_STACK_SIZE

    mov r14, rcx
    mov r13, rdx
    lea r15, [rip + callback_start]
    and r15, -0x10000

    /* Preserve vanilla transfer behavior before touching frame-local copies. */
    mov rcx, r14
    mov rdx, r13
    call qword ptr [r15 + DATA_TRAMPOLINE]

    cmp byte ptr [r15 + DATA_ENABLED], 1
    jne callback_return
    mov r12, qword ptr [r15 + DATA_MAIN]
    test r12, r12
    je callback_return

    mov rbx, qword ptr [r15 + DATA_ROADLAMP_BASE]
    test rbx, rbx
    jne have_roadlamp_base
    lea rax, [r15 + RESOLVE_PLUGIN_BASE]
    call rax
    mov rbx, rax
    test rbx, rbx
    je callback_return
    mov qword ptr [r15 + DATA_ROADLAMP_BASE], rbx

have_roadlamp_base:
    mov r10, qword ptr [rbx + ROADLAMP_EDITOR]
    test r10, r10
    je callback_return
    mov rax, qword ptr [r10 + EDITOR_ACTIVE]
    lea rcx, [rbx + ROADLAMP_DESC]
    cmp rax, rcx
    jne callback_return

    /* The current editor's ordinary-road system owns the live materials. */
    mov rbp, qword ptr [r10 + EDITOR_ROAD_SYSTEM]
    test rbp, rbp
    je callback_return
    inc dword ptr [r15 + DATA_ACTIVE_SCANS]

    cmp byte ptr [r15 + DATA_ACTIVE_LOGGED], 0
    jne setup_queue_a
    mov byte ptr [r15 + DATA_ACTIVE_LOGGED], 1
    mov rax, qword ptr [r15 + DATA_API]
    test rax, rax
    je setup_queue_a
    mov rax, qword ptr [rax + 0x38]
    test rax, rax
    je setup_queue_a
    lea rcx, [rip + log_active]
    mov rdx, rbp
    mov r8, qword ptr [rbp + MAT_ONEWAY_1]
    mov r9, qword ptr [rbp + MAT_LINE]
    mov r10d, dword ptr [r15 + DATA_ACTIVE_SCANS]
    mov dword ptr [rsp + 0x20], r10d
    call rax

setup_queue_a:
    mov r13d, 'A'
    mov rdi, qword ptr [r12 + QUEUE_A_BEGIN]
    mov rsi, qword ptr [r12 + QUEUE_A_END]
    jmp validate_queue

setup_queue_b:
    mov r13d, 'B'
    mov rdi, qword ptr [r12 + QUEUE_B_BEGIN]
    mov rsi, qword ptr [r12 + QUEUE_B_END]

validate_queue:
    test rdi, rdi
    je queue_finished
    cmp rsi, rdi
    jb queue_finished
    mov rax, rsi
    sub rax, rdi
    cmp rax, MAX_QUEUE_BYTES
    ja queue_finished
    xor edx, edx
    div qword ptr [rip + record_size_qword]
    test rdx, rdx
    jne queue_finished

record_loop:
    cmp rdi, rsi
    jae queue_finished
    mov rbx, qword ptr [rdi + 0x00]
    test rbx, rbx
    je next_record
    cmp qword ptr [rdi + 0x08], 0
    je next_record
    cmp dword ptr [rdi + 0x10], 0
    je next_record
    /* Mode 0 is the green road-overlay path. */
    cmp dword ptr [rdi + 0x1c], 0
    jne next_record

    cmp r13d, 'A'
    jne candidate_b
    cmp byte ptr [r15 + DATA_CAND_A_LOGGED], 0
    jne compare_material
    mov byte ptr [r15 + DATA_CAND_A_LOGGED], 1
    jmp log_candidate

candidate_b:
    cmp byte ptr [r15 + DATA_CAND_B_LOGGED], 0
    jne compare_material
    mov byte ptr [r15 + DATA_CAND_B_LOGGED], 1

log_candidate:
    mov rax, qword ptr [r15 + DATA_API]
    test rax, rax
    je compare_material
    mov rax, qword ptr [rax + 0x38]
    test rax, rax
    je compare_material
    mov rcx, qword ptr [rbp + MAT_ONEWAY_1]
    mov qword ptr [rsp + 0x20], rcx
    mov rcx, qword ptr [rbp + MAT_ONEWAY_2]
    mov qword ptr [rsp + 0x28], rcx
    lea rcx, [rip + log_candidate_fmt]
    mov edx, r13d
    mov r8, rdi
    mov r9, rbx
    call rax

compare_material:
    mov r14, qword ptr [rbp + MAT_LINE]
    cmp rbx, qword ptr [rbp + MAT_ONEWAY_1]
    je rewrite_record
    cmp rbx, qword ptr [rbp + MAT_ONEWAY_2]
    je rewrite_record
    cmp rbx, qword ptr [rbp + MAT_ONEWAY_LANE_1]
    je rewrite_record
    cmp rbx, qword ptr [rbp + MAT_ONEWAY_LANE_2]
    je rewrite_record
    mov r14, qword ptr [rbp + MAT_LINE_BP]
    cmp rbx, qword ptr [rbp + MAT_ONEWAY_BP_1]
    je rewrite_record
    cmp rbx, qword ptr [rbp + MAT_ONEWAY_BP_2]
    jne next_record

rewrite_record:
    test r14, r14
    je next_record
    cmp r14, rbx
    je next_record
    mov qword ptr [rdi + 0x00], r14
    inc dword ptr [r15 + DATA_REWRITE_COUNT]

    cmp byte ptr [r15 + DATA_REWRITE_LOGGED], 0
    jne next_record
    mov byte ptr [r15 + DATA_REWRITE_LOGGED], 1
    mov rax, qword ptr [r15 + DATA_API]
    test rax, rax
    je next_record
    mov rax, qword ptr [rax + 0x38]
    test rax, rax
    je next_record
    mov qword ptr [rsp + 0x20], r14
    mov ecx, dword ptr [r15 + DATA_REWRITE_COUNT]
    mov dword ptr [rsp + 0x28], ecx
    lea rcx, [rip + log_rewrite]
    mov edx, r13d
    mov r8, rdi
    mov r9, rbx
    call rax

next_record:
    add rdi, RECORD_SIZE
    jmp record_loop

queue_finished:
    cmp r13d, 'A'
    je setup_queue_b

callback_return:
    add rsp, LOCAL_STACK_SIZE
    pop rbx
    pop rbp
    pop rdi
    pop rsi
    pop r12
    pop r13
    pop r14
    pop r15
    ret
.global callback_end
callback_end:

.p2align 3
record_size_qword:
    .quad RECORD_SIZE

.p2align 4
log_active:
    .asciz "roadlamps.preview active roadSystem=%p oneway1=%p line=%p scan=%u"
log_candidate_fmt:
    .asciz "roadlamps.preview candidate queue=%c record=%p material=%p liveOne1=%p liveOne2=%p"
log_rewrite:
    .asciz "roadlamps.preview arrows hidden queue=%c record=%p material=%p->%p count=%u"

.global code_end
code_end:
