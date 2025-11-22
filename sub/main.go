package main

import (
    "context"
    "database/sql"
    "encoding/json"
    "fmt"
    "log"
    "time"

    "github.com/nats-io/nats.go"
    _ "github.com/lib/pq"
)

// Your message struct
type Message struct {
        Timestamp time.Time `json:"timestamp"`
        Label     string    `json:"label"`
        Value     int       `json:"value"`
        Mac       string    `json:"mac"`
        IP        string    `json:"ip"`
        Factor    float32   `json:"factor"`
        Reading   float32   `json:"reading"`
        Measurement float32 `json:"measurement"`
        Metric    int       `json:"metric"`
        DFI       int       `json:"dfi"`
}


func main() {
    // --- Connect to Postgres ---
    db, err := sql.Open("postgres", "postgres://admin:password123@postgres:5432/eventlog?sslmode=disable")
    if err != nil {
        log.Fatal("postgres connect:", err)
    }
    defer db.Close()

    // Make sure DB is reachable
    if err := db.Ping(); err != nil {
        log.Fatal("postgres ping:", err)
    }
    fmt.Println("Connected to Postgres")


    // --- Connect to NATS ---
    nc, err := nats.Connect("nats://nats:4222")
    if err != nil {
        log.Fatal("nats connect:", err)
    }
    defer nc.Close()

    fmt.Println("Connected to NATS, waiting for messages...")

    // --- Subscribe ---
    _, err = nc.Subscribe("eventstream.>", func(m *nats.Msg) {
        var msg Message

        // Decode JSON
        if err := json.Unmarshal(m.Data, &msg); err != nil {
            log.Println("decode error:", err)
            return
        }
	fmt.Println("message read from nats")
	fmt.Printf("%v", msg)

	// insert into postgres
	_, err := db.ExecContext(
	    context.Background(),
	    `INSERT INTO general (
		timestamp,
		source_mac,
		source_ip,
		value,
		factor,
		reading,
		measurement,
		metric,
		data_field_index
	    ) VALUES (
		$1, $2, $3, $4, $5, $6, $7, $8, $9
	    )`,
	    msg.Timestamp.Unix(),
	    msg.Mac,
	    msg.IP,
	    msg.Value,
	    msg.Factor,
	    msg.Reading,
	    msg.Measurement,
	    msg.Metric,
	    msg.DFI,
	)
	if err != nil {
	    log.Println("db insert error:", err)
	    return
	}

        fmt.Printf("Inserted event: %s (%s)\n", msg.Label, msg.Timestamp.Format(time.RFC3339))
    })
    if err != nil {
        log.Fatal("subscribe:", err)
    }

    // Keep running forever
    select {}
}

