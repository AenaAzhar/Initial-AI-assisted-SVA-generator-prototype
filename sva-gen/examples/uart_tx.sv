// Minimal UART transmitter: 8-N-1, no parity, no flow control.
// Configurable baud divisor; tx_busy held high during transmission.

module uart_tx #(
    parameter int BAUD_DIV = 868
) (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       start,
    input  logic [7:0] data,
    output logic       tx,
    output logic       busy
);
    typedef enum logic [1:0] { IDLE, START_BIT, DATA_BITS, STOP_BIT } state_t;
    state_t state;

    logic [9:0] baud_cnt;
    logic [2:0] bit_idx;
    logic [7:0] shift;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            state    <= IDLE;
            tx       <= 1'b1;
            busy     <= 1'b0;
            baud_cnt <= '0;
            bit_idx  <= '0;
            shift    <= '0;
        end else begin
            unique case (state)
                IDLE: begin
                    tx   <= 1'b1;
                    busy <= 1'b0;
                    if (start) begin
                        state    <= START_BIT;
                        shift    <= data;
                        busy     <= 1'b1;
                        baud_cnt <= BAUD_DIV - 1;
                        tx       <= 1'b0;
                    end
                end
                START_BIT: begin
                    if (baud_cnt == 0) begin
                        state    <= DATA_BITS;
                        baud_cnt <= BAUD_DIV - 1;
                        bit_idx  <= '0;
                        tx       <= shift[0];
                        shift    <= {1'b0, shift[7:1]};
                    end else baud_cnt <= baud_cnt - 1;
                end
                DATA_BITS: begin
                    if (baud_cnt == 0) begin
                        baud_cnt <= BAUD_DIV - 1;
                        if (bit_idx == 7) begin
                            state <= STOP_BIT;
                            tx    <= 1'b1;
                        end else begin
                            bit_idx <= bit_idx + 1;
                            tx      <= shift[0];
                            shift   <= {1'b0, shift[7:1]};
                        end
                    end else baud_cnt <= baud_cnt - 1;
                end
                STOP_BIT: begin
                    if (baud_cnt == 0) begin
                        state <= IDLE;
                        busy  <= 1'b0;
                    end else baud_cnt <= baud_cnt - 1;
                end
            endcase
        end
    end
endmodule