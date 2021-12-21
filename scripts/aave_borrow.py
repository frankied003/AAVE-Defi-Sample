# swap eth for weth, than deposit into contract
from brownie import interface, config, network
from scripts.helpful_scripts import get_account
from web3 import Web3

# 0.1
AMOUNT = Web3.toWei(0.1, "ether")

# can only do transactions with Weth in AAVE
def get_weth():
    account = get_account()
    weth = interface.IWeth(config["networks"][network.show_active()]["weth_token"])
    tx = weth.deposit({"from": account, "value": 0.1 * 10 ** 18})
    tx.wait(1)
    print("Deposited WETH")


def get_lending_pool():
    lending_pool_addresses_provider = interface.ILendingPoolAddressesProvider(
        config["networks"][network.show_active()]["lending_pool_addresses_provider"]
    )
    lending_pool_address = lending_pool_addresses_provider.getLendingPool()
    lending_pool = interface.ILendingPool(lending_pool_address)
    return lending_pool


# WETH have a function where you can approve them to be used by someone else, here its AAVE
def approve_erc20(amount, spender, erc20_address, account):
    print("Aprroving ERC20 token...")
    erc20 = interface.IERC20(erc20_address)
    tx = erc20.approve(spender, amount, {"from": account})
    tx.wait(1)
    print("Approved!")
    return tx


def get_borrowable_data(lending_pool, account):
    (
        total_collateral_eth,
        total_debt_eth,
        available_borrow_eth,
        current_liquidation_eth,
        ltv,
        health_factor,
    ) = lending_pool.getUserAccountData(account.address)

    available_borrow_eth = Web3.fromWei(available_borrow_eth, "ether")
    total_collateral_eth = Web3.fromWei(total_collateral_eth, "ether")
    total_debt_eth = Web3.fromWei(total_debt_eth, "ether")
    print(f"You have {total_collateral_eth} worth of ETH deposited.")
    print(f"You have {total_debt_eth} worth of ETH borrowed.")
    print(f"You have {available_borrow_eth} worth of ETH to borrow.")
    return (float(available_borrow_eth), float(total_debt_eth))


def get_asset_price(price_feed_address):
    dai_eth_price_feed = interface.AggregatorV3Interface(price_feed_address)
    latest_price = dai_eth_price_feed.latestRoundData()[1]
    converted_price = Web3.fromWei(latest_price, "ether")
    print(f"The DAI/ETH price is {converted_price}")
    return float(converted_price)


def repay_all(amount, lending_pool, account):
    # have to approve the dai token
    approve_erc20(
        Web3.toWei(amount, "ether"),
        lending_pool,
        config["networks"][network.show_active()]["dai_token"],
        account,
    )
    repay_tx = lending_pool.repay(
        config["networks"][network.show_active()]["dai_token"],
        amount,
        1,
        account.address,
        {"from": account},
    )
    repay_tx.wait(1)
    print("Repayed!")


def borrow():
    account = get_account()

    # getting WETH
    erc20_address = config["networks"][network.show_active()]["weth_token"]

    get_weth()

    # getting lending pool, and approving that WETH, and then Deposting that WETH
    lending_pool = get_lending_pool()
    approve_erc20(AMOUNT, lending_pool.address, erc20_address, account)
    print("Depositing...")
    tx = lending_pool.deposit(
        erc20_address, AMOUNT, account.address, 0, {"from": account}
    )
    tx.wait(1)
    print("Deposited!")
    borrowable_eth, total_debt = get_borrowable_data(lending_pool, account)

    # getting price of DAI
    dai_eth_price = get_asset_price(
        config["networks"][network.show_active()]["dai_eth_price_feed"]
    )

    # borrow some DAI
    amount_dai_to_borrow = (1 / dai_eth_price) * (borrowable_eth * 0.80)
    print(f"We are going to borrow {amount_dai_to_borrow}")
    dai_address = config["networks"][network.show_active()]["dai_token"]
    borrow_tx = lending_pool.borrow(
        dai_address,
        Web3.toWei(amount_dai_to_borrow, "ether"),
        1,
        0,
        account.address,
        {"from": account},
    )
    borrow_tx.wait(1)
    print("Borrowed some DAI!")
    get_borrowable_data(lending_pool, account)

    # Repay
    # repay_all(AMOUNT, lending_pool, account)
    print("You just completed and loan and payed it off!")


def main():
    borrow()
