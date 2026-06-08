library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity FFT_buffer_out_v2 is
  Generic (
    FFT_size : integer := 256;
    N_bits : integer := 16;
    N_chan : integer := 8
  );
  Port (
    i_clk : in std_logic;
    i_Tvalid : in std_logic;
    i_FFT_word : in std_logic_vector(2*N_bits-1 downto 0); -- Para magnitud al cuadrado quitar -1

    i_SPI_busy : in std_logic;

    o_SPI_tx : out std_logic_vector(N_bits-1 downto 0);  -- MITAD DEL TAMAÑO DE ENTRADA
    o_SPI_enable : out std_logic;
    
    --DEBUG
    debug_write_enable: out std_logic;
    debug_read_enable: out std_logic
  );
end FFT_buffer_out_v2;

architecture Behavioral of FFT_buffer_out_v2 is

    type FFT_multichannel_window is array (0 to N_chan*FFT_size-1)
        of std_logic_vector(2*N_bits-1 downto 0);  -- Para magnitud al cuadrado quitar -1

    signal FFT_buffer : FFT_multichannel_window; 

    signal old_Tvalid : std_logic := '0';
    signal read_enable : std_logic := '0';
    signal write_enable : std_logic := '0';

    signal read_counter  : integer range 0 to N_chan*FFT_size-1 := 0;
    signal write_counter : integer range 0 to 2*N_chan*FFT_size-1 := 0; -- DOBLE DE GRANDE
    

    signal busy_d   : std_logic := '1';
    signal spi_ready : std_logic := '0';
    
    --DEBUG
    signal idx : integer range 0 to 2*N_chan*FFT_size-1;
    signal parity: std_logic;
    
begin

    --DEBUG
    debug_read_enable <= read_enable;
    debug_write_enable <= write_enable;
    --------------------------------------------------------------------
    -- 1) ESCRITURA EN BRAM (proceso limpio)
    --------------------------------------------------------------------
    write_proc : process(i_clk)
    begin
        if rising_edge(i_clk) then
            if read_enable = '1' then
                FFT_buffer(read_counter) <= i_FFT_word;
            end if;
        end if;
    end process;

    --------------------------------------------------------------------
    -- 2) LECTURA DESDE BRAM (proceso limpio)
    --------------------------------------------------------------------
    read_proc : process(i_clk)
    begin
        if rising_edge(i_clk) then
            -- Si el índice es par, se mandan los 16 bits más significativos.
            if (write_counter mod 2) = 0 then
                idx <= write_counter/2;
                parity <='0';
                o_SPI_tx <= FFT_buffer(write_counter/2)(2*N_bits-1 downto N_bits);
            -- Si el índice es impar, se mandan los 16 bits menos significativos.    
            else
                idx <= write_counter/2;
                parity <='1';
                o_SPI_tx <= FFT_buffer(write_counter/2)(N_bits-1 downto 0);
            end if;
            
        end if;
    end process;

    --------------------------------------------------------------------
    -- 3) LÓGICA DE CONTROL
    --------------------------------------------------------------------
    control_proc : process(i_clk)
    begin
        if rising_edge(i_clk) then
            
            -- INICIALIZACIÓN DEL PROCESO DE LECTURA
            -- 1. Detección de flanco de subida -> reset contadores, comienzo lectura.
            old_Tvalid <= i_Tvalid;
            if old_Tvalid = '0' and i_Tvalid = '1' then
                read_enable <= '1';
                read_counter <= 0;
                write_enable <= '0';
                write_counter <= 0;
            end if;
            
           
            -- PROCESO DE ESCRITURA
            --3. Se inicia solo si se leen los datos completos.
            
            -- Control del busy SPI.
            busy_d <= i_SPI_busy;
            if (busy_d = '1' and i_SPI_busy = '0') then
                spi_ready <= '1';
            else
                spi_ready <= '0';
            end if;
            
            if write_enable = '1' then
                if spi_ready = '1' then
                    o_SPI_enable <= '1';
                    if write_counter <  2*N_chan*FFT_size-1 then
                        write_counter <= (write_counter + 1);
                    else
                        write_counter <= 0;
                        
                    end if;
                else
                    o_SPI_enable <= '0';
                end if;

                if write_counter = 0 then -- RANGO CORREGIDO
                    write_enable <= '0';
                    o_SPI_enable <= '0';
                end if;
            else
                o_SPI_enable <= '0';
            end if;
            
             -- PROCESO DE LECTURA
            --2. La condición de final de lectura es el contador. Si faltan datos, se reseteará en el siguente ciclo.
            if read_enable = '1' then
                if read_counter = N_chan*FFT_size-1 then
                    read_enable <= '0';
                    write_enable <= '1';
                    read_counter <= 0;

                    o_SPI_enable <= '1';
                    write_counter <= 1; 
                else
                    read_counter <= read_counter + 1;
                end if;
            end if;
            
            
        end if;
    end process;
end Behavioral;
