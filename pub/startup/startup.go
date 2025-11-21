package startup

import (
	"fmt"
	"net"
	"os/exec"
	"runtime"
	"strings"
)

var (
	LocalIP  string
	CIDR     string
	DeviceIP string
)

// Init runs all network discovery steps
func Init(targetMac string) error {
	ip, cidr, err := getLocalNetwork()
	if err != nil {
		return fmt.Errorf("network not connected: %w", err)
	}

	LocalIP = ip
	CIDR = cidr

	ipFromMac, err := findIPFromMAC(targetMac)
	if err != nil {
		return fmt.Errorf("mac lookup failed: %w", err)
	}

	DeviceIP = ipFromMac
	return nil
}

// -------------------------------------------
// Internal (private) functions
// -------------------------------------------

func getLocalNetwork() (string, string, error) {
	ifaces, err := net.Interfaces()
	if err != nil {
		return "", "", err
	}

	for _, iface := range ifaces {
		if iface.Flags&net.FlagUp == 0 || iface.Flags&net.FlagLoopback != 0 {
			continue
		}

		addrs, _ := iface.Addrs()
		for _, addr := range addrs {
			ipNet, ok := addr.(*net.IPNet)
			if !ok {
				continue
			}

			ip := ipNet.IP
			if ip == nil || ip.To4() == nil {
				continue
			}

			return ip.String(), ipNet.String(), nil
		}
	}

	return "", "", fmt.Errorf("no network connection found")
}

func findIPFromMAC(mac string) (string, error) {
	mac = strings.ToLower(strings.ReplaceAll(mac, "-", ":"))

	arpTable, err := readARPTable()
	if err != nil {
		return "", err
	}

	for ip, arpMac := range arpTable {
		if strings.ToLower(arpMac) == mac {
			return ip, nil
		}
	}

	return "", nil
}

func readARPTable() (map[string]string, error) {
	switch runtime.GOOS {
	case "linux":
		return parseArpOutput(exec.Command("cat", "/proc/net/arp"))
	case "darwin", "windows":
		return parseArpOutput(exec.Command("arp", "-a"))
	default:
		return nil, fmt.Errorf("unsupported OS")
	}
}

func parseArpOutput(cmd *exec.Cmd) (map[string]string, error) {
	data, err := cmd.Output()
	if err != nil {
		return nil, err
	}

	lines := strings.Split(string(data), "\n")
	results := map[string]string{}

	for _, line := range lines {
		fields := strings.Fields(line)
		if len(fields) < 3 {
			continue
		}

		// Linux (/proc/net/arp)
		if strings.Count(line, ":") == 5 && strings.Contains(line, ".") && len(fields) >= 4 {
			ip := fields[0]
			mac := fields[3]
			results[ip] = mac
			continue
		}

		// macOS / Windows (arp -a)
		if strings.Contains(line, "(") && strings.Contains(line, ")") && strings.Contains(line, " at ") {
			ip := line[strings.Index(line, "(")+1 : strings.Index(line, ")")]
			parts := strings.Split(line, " at ")
			if len(parts) < 2 {
				continue
			}
			afterAt := strings.Fields(parts[1])
			if len(afterAt) > 0 {
				results[ip] = afterAt[0]
			}
		}
	}

	return results, nil
}

