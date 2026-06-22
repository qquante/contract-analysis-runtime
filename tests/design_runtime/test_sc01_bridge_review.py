from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vassago_contract_runtime.artifacts.store import ArtifactStore
from vassago_contract_runtime.design_runtime.manifest import create_run_manifest
from vassago_contract_runtime.design_runtime.models import ContractTarget, DesignSpec, PhaseSpec
from vassago_contract_runtime.sc01_bridge_review import build_bridge_current_review, write_sc01_bridge_current_review


class Sc01BridgeReviewTests(unittest.TestCase):
    def test_layerzero_v1_endpoint_and_trusted_remote_are_ready_for_state_review(self) -> None:
        review = build_bridge_current_review(_source_manifest("LayerZeroApp.sol", _layerzero_source(), abi=[
            {"type": "function", "name": "lzReceive", "inputs": [], "outputs": []},
            {"type": "function", "name": "trustedRemoteLookup", "inputs": [], "outputs": []},
        ]))

        self.assertEqual(review["summary"]["verdict"], "bridge_paths_ready_for_current_state_review")
        protocols = {item["protocol"] for item in review["protocol_fingerprints"]}
        self.assertIn("layerzero_v1", protocols)
        endpoint = _path(review, "endpoint_source_validation")
        self.assertEqual(endpoint["status"], "candidate_ready_for_state_review")
        self.assertEqual(endpoint["next_required_review"], "read_endpoint_and_peer_state")

    def test_axelar_execute_without_validate_contract_call_is_blocked(self) -> None:
        review = build_bridge_current_review(_source_manifest("AxelarBad.sol", _axelar_bad_source(), abi=[
            {"type": "function", "name": "execute", "inputs": [], "outputs": []},
        ]))

        endpoint = _path(review, "endpoint_source_validation")
        self.assertEqual(endpoint["status"], "blocked_missing_source_validation_signal")
        self.assertEqual(review["summary"]["current_live_risk"], "not_claimed")

    def test_hyperlane_handle_with_mailbox_guard_and_asset_transfer_needs_delta(self) -> None:
        review = build_bridge_current_review(_source_manifest("HyperlaneRecipient.sol", _hyperlane_source(), abi=[
            {"type": "function", "name": "handle", "inputs": [], "outputs": []},
            {"type": "function", "name": "balanceOf", "inputs": [], "outputs": []},
        ]))

        protocols = {item["protocol"] for item in review["protocol_fingerprints"]}
        self.assertIn("hyperlane", protocols)
        self.assertEqual(_path(review, "endpoint_source_validation")["status"], "candidate_ready_for_state_review")
        self.assertEqual(_path(review, "recipient_asset_moving")["status"], "candidate_ready_for_state_review")

    def test_nomad_root_proof_path_maps_to_root_state_review(self) -> None:
        review = build_bridge_current_review(_source_manifest("Replica.sol", _nomad_source(), abi=[
            {"type": "function", "name": "process", "inputs": [], "outputs": []},
            {"type": "function", "name": "acceptableRoot", "inputs": [], "outputs": []},
            {"type": "function", "name": "confirmAt", "inputs": [], "outputs": []},
        ]))

        protocols = {item["protocol"] for item in review["protocol_fingerprints"]}
        self.assertIn("nomad_replica", protocols)
        root = _path(review, "root_proof_verifier")
        self.assertEqual(root["status"], "candidate_ready_for_state_review")
        self.assertEqual(root["next_required_review"], "read_root_proof_state")

    def test_writer_creates_bridge_review_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            target = ContractTarget("eth", "0x1111111111111111111111111111111111111111")
            design = DesignSpec(
                design_id="sc01-access",
                version="test",
                title="Test",
                target_model="ContractTarget",
                phases=(PhaseSpec("01_dossier", "Dossier"), PhaseSpec("05_source_truth", "Source Truth")),
            )
            create_run_manifest(run_dir, design, [target])
            store = ArtifactStore(run_dir, json.loads((run_dir / "run-manifest.json").read_text())["run_id"])
            store.write_json_artifact(target.target_id, "01_dossier", "source-manifest.json", _source_manifest("LayerZeroApp.sol", _layerzero_source()))
            store.write_json_artifact(target.target_id, "05_source_truth", "sc01-source-truth.json", {"status": "source_truth_verified"})

            result = write_sc01_bridge_current_review(run_dir, target.target_id)

            self.assertEqual(result["status"], "completed")
            artifact = json.loads(
                (run_dir / "targets" / target.target_id / "phases" / "12_current_state_review" / "sc01-bridge-current-review.json").read_text()
            )
            self.assertEqual(artifact["summary"]["current_live_risk"], "not_claimed")


def _path(review: dict, path_id: str) -> dict:
    return next(item for item in review["path_reviews"] if item["path_id"] == path_id)


def _source_manifest(name: str, source: str, abi: list[dict] | None = None) -> dict:
    return {
        "target": {"chain": "eth", "address": "0x1111111111111111111111111111111111111111"},
        "abi": abi or [],
        "source_files": {name: source},
    }


def _layerzero_source() -> str:
    return """
    contract LayerZeroApp {
        address public lzEndpoint;
        mapping(uint16 => bytes) public trustedRemoteLookup;
        function lzReceive(uint16 _srcChainId, bytes calldata _srcAddress, uint64, bytes calldata) external {
            require(msg.sender == lzEndpoint, "invalid endpoint caller");
            bytes memory trustedRemote = trustedRemoteLookup[_srcChainId];
            require(_srcAddress.length == trustedRemote.length && keccak256(_srcAddress) == keccak256(trustedRemote), "!trusted");
        }
    }
    """


def _axelar_bad_source() -> str:
    return """
    contract AxelarBad {
        function execute(string calldata sourceChain, string calldata sourceAddress, bytes calldata payload) external {
            _do(payload);
        }
        function _do(bytes calldata payload) internal {}
    }
    """


def _hyperlane_source() -> str:
    return """
    interface IERC20 { function transfer(address to, uint256 amount) external returns (bool); }
    contract HyperlaneRecipient {
        address public mailbox;
        IERC20 public token;
        function handle(uint32, bytes32, bytes calldata) external {
            require(msg.sender == mailbox, "!mailbox");
            token.transfer(address(0xBEEF), 1);
        }
    }
    """


def _nomad_source() -> str:
    return """
    contract Replica {
        mapping(bytes32 => uint256) public confirmAt;
        mapping(bytes32 => bytes32) public messages;
        function process(bytes memory message) public returns (bool) {
            bytes32 messageHash = keccak256(message);
            require(acceptableRoot(messages[messageHash]), "!proven");
            return true;
        }
        function prove(bytes32, bytes32[32] calldata, uint256) public returns (bool) {}
        function acceptableRoot(bytes32 root) public view returns (bool) { return confirmAt[root] != 0; }
    }
    """


if __name__ == "__main__":
    unittest.main()
