.intel_syntax noprefix
.section .text

/*
 * calc_safe_span(rcx = target) -> eax = whole-instruction span >= 14, or 0.
 *
 * This intentionally accepts only ordinary position-independent compiler
 * prologue instructions: register pushes, MOV/LEA using ModRM addressing, and
 * group-1 immediate operations such as SUB RSP.  RIP-relative and control-flow
 * instructions are rejected instead of being copied into a trampoline.
 */

.global span_decoder
span_decoder:
    xor eax, eax

next_instruction:
    cmp eax, 14
    jae span_ok
    cmp eax, 32
    jae span_fail
    lea r8, [rcx + rax]
    xor r9d, r9d

    /* Optional single REX prefix. */
    movzx edx, byte ptr [r8]
    cmp dl, 0x40
    jb opcode_ready
    cmp dl, 0x4f
    ja opcode_ready
    inc r9d
    movzx edx, byte ptr [r8 + 1]

opcode_ready:
    /* PUSH r64. */
    cmp dl, 0x50
    jb not_push
    cmp dl, 0x57
    jbe accept_one
not_push:
    /* MOV or LEA with a ModRM byte. */
    cmp dl, 0x89
    je modrm_no_imm
    cmp dl, 0x8b
    je modrm_no_imm
    cmp dl, 0x8d
    je modrm_no_imm
    /* Group-1 immediate instructions (commonly SUB RSP). */
    cmp dl, 0x81
    je modrm_imm32
    cmp dl, 0x83
    je modrm_imm8
    jmp span_fail

accept_one:
    add r9d, 1
    add eax, r9d
    jmp next_instruction

modrm_imm32:
    mov r10d, 4
    jmp parse_modrm
modrm_imm8:
    mov r10d, 1
    jmp parse_modrm
modrm_no_imm:
    xor r10d, r10d

parse_modrm:
    /* Prefix + opcode + ModRM. */
    add r9d, 2
    movzx edx, byte ptr [r8 + r9 - 1]
    mov r11d, edx
    shr r11d, 6
    and edx, 7
    cmp r11d, 3
    je add_immediate

    /* SIB follows when r/m == 4. */
    cmp edx, 4
    jne no_sib
    movzx edx, byte ptr [r8 + r9]
    inc r9d
    and edx, 7
    /* mod=0 with SIB base=5 carries disp32 and is position-independent. */
    test r11d, r11d
    jne displacement
    cmp edx, 5
    jne add_immediate
    add r9d, 4
    jmp add_immediate

no_sib:
    /* mod=0, r/m=5 is RIP-relative: reject it. */
    test r11d, r11d
    jne displacement
    cmp edx, 5
    je span_fail
    jmp add_immediate

displacement:
    cmp r11d, 1
    jne displacement_32
    inc r9d
    jmp add_immediate
displacement_32:
    cmp r11d, 2
    jne span_fail
    add r9d, 4

add_immediate:
    add r9d, r10d
    add eax, r9d
    jmp next_instruction

span_ok:
    cmp eax, 32
    jbe span_return
span_fail:
    xor eax, eax
span_return:
    ret

.global span_decoder_end
span_decoder_end:

