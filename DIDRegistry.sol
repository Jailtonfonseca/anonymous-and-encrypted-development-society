// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title DIDRegistry
 * @dev A simple smart contract for managing Decentralized Identifiers (DIDs).
 * Allows registration of DIDs, and updating their associated public key and document CID.
 */
contract DIDRegistry {

    // Structure to store DID information
    struct DIDData {
        address owner;        // The Ethereum address that controls the DID
        string publicKey;     // A string representing the public key (e.g., base58 encoded)
        string documentCID;   // IPFS CID of an associated DID document
        bool isRegistered;    // Flag to check if a DID is registered
    }

    // Mapping from the DID (bytes32) to its data
    mapping(bytes32 => DIDData) private dids;

    // Events
    event DIDRegistered(bytes32 indexed did, address indexed owner, string publicKey, string documentCID);
    event PublicKeyUpdated(bytes32 indexed did, address indexed newOwner, string newPublicKey);
    event DocumentCIDUpdated(bytes32 indexed did, address indexed owner, string newDocumentCID);

    /**
     * @dev Registers a new DID.
     * The msg.sender becomes the owner of this DID.
     * @param did The DID identifier (bytes32).
     * @param _publicKey The initial public key associated with the DID.
     * @param _documentCID The initial IPFS CID of the DID document.
     */
    function registerDID(bytes32 did, string memory _publicKey, string memory _documentCID) public {
        require(!dids[did].isRegistered, "DIDRegistry: DID is already registered.");
        
        dids[did] = DIDData({
            owner: msg.sender,
            publicKey: _publicKey,
            documentCID: _documentCID,
            isRegistered: true
        });

        emit DIDRegistered(did, msg.sender, _publicKey, _documentCID);
    }

    /**
     * @dev Updates the public key for an existing DID.
     * Only the owner of the DID can perform this update.
     * @param did The DID identifier.
     * @param _newPublicKey The new public key.
     */
    function updatePublicKey(bytes32 did, string memory _newPublicKey) public {
        require(dids[did].isRegistered, "DIDRegistry: DID not found.");
        require(dids[did].owner == msg.sender, "DIDRegistry: Caller is not the owner of the DID.");

        dids[did].publicKey = _newPublicKey;
        emit PublicKeyUpdated(did, msg.sender, _newPublicKey);
    }

    /**
     * @dev Updates the document CID for an existing DID.
     * Only the owner of the DID can perform this update.
     * @param did The DID identifier.
     * @param _newDocumentCID The new IPFS CID for the DID document.
     */
    function updateDocumentCID(bytes32 did, string memory _newDocumentCID) public {
        require(dids[did].isRegistered, "DIDRegistry: DID not found.");
        require(dids[did].owner == msg.sender, "DIDRegistry: Caller is not the owner of the DID.");

        dids[did].documentCID = _newDocumentCID;
        emit DocumentCIDUpdated(did, msg.sender, _newDocumentCID);
    }

    /**
     * @dev Retrieves the owner of a given DID.
     * @param did The DID identifier.
     * @return The Ethereum address of the DID owner.
     */
    function getDIDOwner(bytes32 did) public view returns (address) {
        require(dids[did].isRegistered, "DIDRegistry: DID not found.");
        return dids[did].owner;
    }

    /**
     * @dev Retrieves the public key associated with a given DID.
     * @param did The DID identifier.
     * @return The public key string.
     */
    function getPublicKey(bytes32 did) public view returns (string memory) {
        require(dids[did].isRegistered, "DIDRegistry: DID not found.");
        return dids[did].publicKey;
    }

    /**
     * @dev Retrieves the document CID associated with a given DID.
     * @param did The DID identifier.
     * @return The document CID string.
     */
    function getDocumentCID(bytes32 did) public view returns (string memory) {
        require(dids[did].isRegistered, "DIDRegistry: DID not found.");
        return dids[did].documentCID;
    }
    
    /**
     * @dev Retrieves all information (owner, public key, document CID) for a given DID.
     * @param did The DID identifier.
     * @return owner The Ethereum address of the DID owner.
     * @return publicKey The public key string.
     * @return documentCID The document CID string.
     */
    function getDIDInfo(bytes32 did) public view returns (address owner, string memory publicKey, string memory documentCID) {
        require(dids[did].isRegistered, "DIDRegistry: DID not found.");
        DIDData storage data = dids[did];
        return (data.owner, data.publicKey, data.documentCID);
    }

    /**
     * @dev Checks if a DID is registered.
     * @param did The DID identifier.
     * @return True if the DID is registered, false otherwise.
     */
    function isDIDRegistered(bytes32 did) public view returns (bool) {
        return dids[did].isRegistered;
    }
}
