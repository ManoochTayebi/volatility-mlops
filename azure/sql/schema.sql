IF SCHEMA_ID('dbo') IS NULL
    EXEC('CREATE SCHEMA [dbo]');

IF OBJECT_ID('dbo.daily_stock_prices', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.daily_stock_prices (
        [datetime] date NOT NULL,
        [symbol] varchar(16) NOT NULL,
        [open] float NOT NULL,
        [high] float NOT NULL,
        [low] float NOT NULL,
        [close] float NOT NULL,
        [volume] bigint NULL,
        [created_at] datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        [updated_at] datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [pk_daily_stock_prices_symbol_datetime]
            PRIMARY KEY ([symbol], [datetime])
    );
END;
