# SC01 Access Control Design

SC01 asks:

```text
Who is allowed to perform this critical action?
```

For Vassago, a SC01 issue requires:

1. critical effect;
2. missing or wrong authorization;
3. unauthorized actor;
4. codable call path;
5. measurable state or asset delta;
6. local deterministic proof.

Static analysis can find candidates. It cannot prove runtime impact alone.

## Initial Thesis Set

- Missing critical guard.
- Uninitialized implementation/proxy.
- Weak UUPS upgrade authorization.
- Role admin/self-admin escalation.
- `tx.origin` authorization.
- Arbitrary sender/from.
- Bridge endpoint/source validation.
- Hook/callback caller validation.
- Safe module/fallback abuse.
- ERC4337/Kernel validator/module authorization.

## False Positive Patterns

- public user-funded deposit/withdraw;
- lifecycle expiration open by design;
- keeper function with harmless bounded effect;
- `onlyWhenUnlocked` protocol lock guard;
- implementation initialized but proxy unaffected;
- helper/multicall wrapper without sensitive sink;
- view/pure relation calls.
