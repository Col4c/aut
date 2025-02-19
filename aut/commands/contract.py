"""
The `contract` command group
"""

from aut.options import (
    from_option,
    rpc_endpoint_option,
    keyfile_option,
    tx_aux_options,
    contract_options,
)

from click import group, command, option, argument, ClickException
from typing import Optional, List, Tuple

# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=import-outside-toplevel


@group(name="contract")
def contract_group() -> None:
    """
    Command for interacting with arbitrary contracts.
    """


def function_call_from_args(
    rpc_endpoint: Optional[str],
    contract_address_str: Optional[str],
    contract_abi_path: Optional[str],
    method: str,
    parameters: List[str],
) -> Tuple:
    """
    Take command line arguments and construct a ContractFunction
    (i.e. a function call).  Returns the ContractFunction object, the
    ABIFunction for the method, and the Web3 object created in the
    process.
    """

    from aut.logging import log
    from aut.utils import (
        web3_from_endpoint_arg,
        contract_address_and_abi_from_args,
    )

    from autonity.abi_parser import find_abi_function, parse_arguments

    log(f"method: {method}")
    log(f"parameters: {list(parameters)}")

    address, abi = contract_address_and_abi_from_args(
        contract_address_str, contract_abi_path
    )

    abi_fn = find_abi_function(abi, method)
    fn_params = parse_arguments(abi_fn, parameters)
    log(f"fn_params (parsed): {fn_params}")

    w3 = web3_from_endpoint_arg(None, rpc_endpoint)
    contract = w3.eth.contract(address, abi=abi)
    contract_fn = getattr(contract.functions, method, None)
    if contract_fn is None:
        raise ClickException(f"method '{method}' not found on contract abi")

    return contract_fn(*fn_params), abi_fn, w3


@command(name="call")
@rpc_endpoint_option
@contract_options
@argument("method")
@argument("parameters", nargs=-1)
def call_cmd(
    rpc_endpoint: Optional[str],
    contract_address_str: Optional[str],
    contract_abi_path: Optional[str],
    method: str,
    parameters: List[str],
) -> None:
    """
    Execute a contract call on the connected node, and print the result.
    """

    from aut.utils import to_json

    from autonity.abi_parser import parse_return_value

    function, abi_fn, _ = function_call_from_args(
        rpc_endpoint,
        contract_address_str,
        contract_abi_path,
        method,
        parameters,
    )

    result = function.call()
    parsed_result = parse_return_value(abi_fn, result)
    print(to_json(parsed_result))


contract_group.add_command(call_cmd)


@command(name="tx")
@rpc_endpoint_option
@keyfile_option()
@from_option
@contract_options
@tx_aux_options
@option(
    "--value",
    "-v",
    help="value in Auton or whole tokens (e.g. '0.000000007' and '7gwei' are identical).",
)
@argument("method")
@argument("parameters", nargs=-1)
def tx_cmd(
    rpc_endpoint: Optional[str],
    keyfile: Optional[str],
    from_str: Optional[str],
    contract_address_str: Optional[str],
    contract_abi_path: Optional[str],
    method: str,
    parameters: List[str],
    gas: Optional[str],
    gas_price: Optional[str],
    max_priority_fee_per_gas: Optional[str],
    max_fee_per_gas: Optional[str],
    fee_factor: Optional[float],
    nonce: Optional[int],
    value: Optional[str],
    chain_id: Optional[int],
) -> None:
    """
    Create a transaction which calls the given contract method,
    passing any parameters.  The parameters must match those required
    by the contract.
    """

    from aut.logging import log
    from aut.utils import (
        from_address_from_argument,
        create_contract_tx_from_args,
        finalize_tx_from_args,
        to_json,
    )

    function, _, w3 = function_call_from_args(
        rpc_endpoint,
        contract_address_str,
        contract_abi_path,
        method,
        parameters,
    )

    from_addr = from_address_from_argument(from_str, keyfile)
    log(f"from_addr: {from_addr}")

    tx = create_contract_tx_from_args(
        function=function,
        from_addr=from_addr,
        value=value,
        gas=gas,
        gas_price=gas_price,
        max_fee_per_gas=max_fee_per_gas,
        max_priority_fee_per_gas=max_priority_fee_per_gas,
        fee_factor=fee_factor,
        nonce=nonce,
        chain_id=chain_id,
    )

    # Fill in any missing values.

    tx = finalize_tx_from_args(w3, rpc_endpoint, tx, from_addr)
    print(to_json(tx))


contract_group.add_command(tx_cmd)
