// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// Adjusted import paths for local compilation
import "./openzeppelin/contracts/token/ERC20/ERC20.sol";
import "./openzeppelin/contracts/access/Ownable.sol";

/**
 * @title AegisToken
 * @dev Implementation of the $AEGIS Platform Token, an ERC20 compliant token.
 * Total supply of 1,000,000,000 tokens is minted to the deployer.
 */
contract AegisToken is ERC20, Ownable { 
    constructor(address initialOwner) ERC20("Aegis Platform Token", "$AEGIS") {
        _mint(initialOwner, 1000000000 * (10**uint256(decimals())));
        transferOwnership(initialOwner); 
    }
}
