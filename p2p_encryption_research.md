# P2P Encrypted Messaging Layer: Research & Recommendations

This document outlines research and recommendations for implementing a basic peer-to-peer (P2P) encrypted messaging layer for Aegis Forge DIDs.

## 1. P2P Networking (Python, Basic Focus)

The goal is a simple mechanism for two peers to exchange text messages directly.

### Option 1: `libp2p-python` (`py-libp2p`)

*   **Website/Docs:** [https://github.com/libp2p/py-libp2p](https://github.com/libp2p/py-libp2p)
*   **Suitability Assessment:**
    *   `py-libp2p` is the Python implementation of the libp2p networking stack, designed for building decentralized applications.
    *   It offers a comprehensive suite of P2P features, including various transports (TCP, QUIC (experimental)), stream multiplexing, security protocols (Noise (experimental), TLS (missing)), and pub/sub mechanisms (Floodsub, Gossipsub).
    *   The repository contains an `echo` example (`examples/echo/echo.py`) that demonstrates basic two-node communication by setting up a host, listening on a multiaddress, and defining a stream handler. Clients connect using the server's full multiaddress (including PeerID).
    *   **Challenge:** The library is explicitly marked as "experimental and work-in-progress" and not recommended for production. Key P2P features like robust NAT traversal and decentralized discovery mechanisms are still under development or missing. For a *very basic* text exchange where peers might initially only know IP/port, the setup (hosts, multiaddrs, peer IDs, protocol negotiation) can be more involved than simpler socket-based approaches.

### Option 2: Simpler Alternatives (e.g., `asyncio` + `socket`)

*   **Python Standard Library (`asyncio` and `socket`):**
    *   Python's `asyncio` library, particularly its [Streams API](https://docs.python.org/3/library/asyncio-stream.html), provides high-level async/await-ready primitives for network connections.
    *   Functions like `asyncio.open_connection()` (client) and `asyncio.start_server()` (server) allow for straightforward TCP socket programming.
    *   This approach is lightweight as it relies on built-in or standard modules.
    *   **Suitability:** For basic P2P where peers can discover each other's IP address and port (e.g., manual exchange, simple local discovery, or a future simple rendezvous server), this is significantly less complex to implement than `py-libp2p`.
*   **Other libraries (e.g., `zeromq`):** Libraries like ZeroMQ also offer powerful messaging patterns but might introduce their own abstractions and dependencies that could be overkill for a very basic initial P2P layer.

### P2P Networking Recommendation:

For a **basic** P2P encrypted messaging layer in this initial phase, **`asyncio` with Python's built-in `socket` module (Streams API)** is recommended.

*   **Reasoning:** It offers the simplest path to establish direct TCP connections between two peers who can resolve each other's IP address and port. This aligns with the "basic" requirement, minimizing external dependencies and the learning curve associated with more comprehensive but experimental P2P stacks like `py-libp2p`.
*   **Future Consideration:** If more advanced P2P capabilities (decentralized discovery, NAT traversal, various transports) become critical, `py-libp2p` could be revisited.

## 2. End-to-End Encryption Strategy

Messages should be encrypted such that only the intended recipient DID's owner can decrypt them.

### Key Source:

*   Each DID is owned by an Ethereum address, which has an associated secp256k1 key pair (public and private key).
*   The `DIDRegistry.sol` contract stores an `owner` (Ethereum address) and a `publicKey` (string) for each DID.
    *   If the `publicKey` string is a direct representation of the secp256k1 public key (e.g., uncompressed hex), it can be used.
    *   Alternatively, and often more reliably, the public key can be derived from the recipient's Ethereum address (owner of the DID).

### Proposed Encryption Scheme: ECIES

**ECIES (Elliptic Curve Integrated Encryption Scheme)** is recommended, utilizing the Ethereum (secp256k1) key pairs.

*   **Encryption (Sender Alice, Recipient Bob):**
    1.  Alice obtains Bob's secp256k1 public key (associated with Bob's DID/Ethereum address).
    2.  Alice generates a new ephemeral secp256k1 key pair.
    3.  Alice uses ECDH between her ephemeral private key and Bob's public key to derive a shared secret.
    4.  The shared secret is passed through a KDF (Key Derivation Function, e.g., HKDF) to generate symmetric encryption keys (e.g., for AES-256-GCM) and MAC keys (if not part of AEAD).
    5.  The message is encrypted using the symmetric key (AES-256-GCM provides both encryption and integrity).
    6.  The payload sent to Bob includes Alice's ephemeral public key and the ciphertext (and MAC/tag if separate).
*   **Decryption (Bob):**
    1.  Bob uses his private key and Alice's received ephemeral public key to derive the same shared secret via ECDH.
    2.  Bob derives the same symmetric key(s) using the KDF.
    3.  Bob decrypts the ciphertext and verifies integrity using the symmetric key (e.g., AES-GCM tag).

### Recommended Python Libraries for Cryptography:

1.  **`eciespy`**:
    *   **Installation:** `pip install eciespy`
    *   **Use:** Directly implements ECIES. It should be evaluated for compatibility with secp256k1 and ease of use.
2.  **`pynacl`**:
    *   **Installation:** `pip install pynacl`
    *   **Use:** Provides high-level public-key authenticated encryption via `Box` (uses X25519 keys by default, but can be adapted or used as a model if direct ECIES for secp256k1 is needed and `eciespy` isn't suitable). For direct secp256k1 ECIES, lower-level components might be needed if `pynacl` doesn't directly support ECIES with secp256k1.
3.  **`cryptography`**:
    *   **Installation:** `pip install cryptography`
    *   **Use:** Provides low-level cryptographic primitives (AES, GCM, HKDF, elliptic curve operations like ECDH for secp256k1). Can be used to implement ECIES if a direct library is insufficient or for more control.
4.  **`eth_keys`**:
    *   **Installation:** `pip install eth-keys`
    *   **Use:** Essential for handling Ethereum's secp256k1 keys: deriving public keys from private keys, key format conversions, and potentially for signing/verifying message signatures if that feature is added.

**Encryption Library Recommendation:**
*   Primary: Evaluate **`eciespy`** for direct ECIES implementation with secp256k1.
*   Secondary/Alternative: If `eciespy` is not ideal, use a combination of **`cryptography`** (for ECDH with secp256k1, AES-GCM, HKDF) and **`eth_keys`** (for key management). `pynacl` is excellent but its `Box` uses Curve25519; adapting it for secp256k1 ECIES would mean using its lower-level components or a different library.

## 3. Message Structure (Conceptual)

A potential JSON structure for an E2E encrypted P2P message:

```json
{
  "protocol_version": "aegis-p2p-msg/v1.0",
  "sender_did_unique_id": "alice-unique-id", 
  "recipient_did_unique_id": "bob-unique-id",
  "timestamp_utc_iso8601": "2024-05-24T12:34:56.789Z",
  "encrypted_payload": { 
    "type": "ecies_secp256k1_aes256gcm", // Example scheme identifier
    "ephemeral_public_key_hex": "0x...", // Sender's ephemeral public key
    "ciphertext_hex": "0x...",          // Encrypted message content
    "auth_tag_hex": "0x..."             // Authentication tag from AES-GCM
  },
  // Optional, but recommended for sender authenticity
  "signature_hex": "0x..." // Signature of (hash of relevant message fields) by sender's DID private key
}
```
*   `sender_did_unique_id` / `recipient_did_unique_id`: These would be the human-readable unique strings used to identify DIDs in other parts of the system, from which `bytes32` identifiers and associated Ethereum addresses/public keys can be resolved.

## 4. Overall Recommendation Summary

For a **basic but secure E2E encrypted P2P messaging layer** in this phase:

*   **P2P Networking:** Use **`asyncio` Streams API** (from Python's standard library) for direct TCP connections between peers. This assumes peers can discover each other's IP and port through an external mechanism initially.
    *   `pip install` (nothing extra needed beyond Python itself)
*   **End-to-End Encryption:** Implement **ECIES using Ethereum secp256k1 key pairs**.
    *   **Primary Library Choice:** Evaluate **`eciespy`** (`pip install eciespy`).
    *   **Supporting Libraries:** Use **`eth_keys`** (`pip install eth-keys`) for Ethereum key handling. If `eciespy` is insufficient, build ECIES using primitives from the **`cryptography`** library (`pip install cryptography`).

This combination provides a balance of simplicity for the P2P networking aspect and robust, standard-based encryption tied to the existing DID cryptographic identities.
```
