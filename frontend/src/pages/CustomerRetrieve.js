import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function CountdownTimer({ arrivedAt, waitMinutes = 5 }) {
  const [timeLeft, setTimeLeft] = useState(null);

  useEffect(() => {
    if (!arrivedAt) return;
    const deadline = new Date(arrivedAt).getTime() + waitMinutes * 60 * 1000;

    const tick = () => {
      const remaining = Math.max(0, deadline - Date.now());
      setTimeLeft(remaining);
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [arrivedAt]);

  if (timeLeft === null) return null;

  const mins = Math.floor(timeLeft / 60000);
  const secs = Math.floor((timeLeft % 60000) / 1000);
  const expired = timeLeft <= 0;
  const urgent = timeLeft < 60000 && !expired;

  return (
    <div
      className={`retrieve-timer ${expired ? "retrieve-timer-expired" : urgent ? "retrieve-timer-urgent" : ""}`}
      data-testid="retrieve-countdown"
    >
      <p style={{ fontSize: 12, color: "#a1a1aa", marginBottom: 4 }}>
        {expired ? "TIME EXPIRED" : "Time remaining to collect"}
      </p>
      <p className="retrieve-timer-digits">
        {expired ? "0:00" : `${mins}:${secs.toString().padStart(2, "0")}`}
      </p>
      {expired && (
        <p style={{ fontSize: 12, color: "#f87171", marginTop: 4 }}>
          Your car may be returned to parking
        </p>
      )}
    </div>
  );
}

export default function CustomerRetrieve() {
  const { vehicleId } = useParams();
  const [vehicle, setVehicle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    fetchVehicle();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [vehicleId]);

  const fetchVehicle = async () => {
    try {
      const res = await axios.get(`${API}/retrieve/${vehicleId}`);
      setVehicle(res.data);
      // Start polling if there's an active ticket
      if (res.data.active_ticket_status && !["pending_payment"].includes(res.data.active_ticket_status)) {
        startPolling();
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Vehicle not found");
    } finally {
      setLoading(false);
    }
  };

  const startPolling = () => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      try {
        const res = await axios.get(`${API}/retrieve/${vehicleId}`);
        setVehicle(res.data);
        // Stop polling if vehicle is checked out or no active ticket
        if (res.data.status === "checked_out" || !res.data.active_ticket_status) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch (err) {
        console.warn('Customer retrieval poll failed:', err.message);
      }
    }, 5000);
  };

  const handleConfirm = async () => {
    setConfirming(true);
    try {
      const res = await axios.post(`${API}/retrieve/${vehicleId}/confirm`);
      setResult(res.data);
      // After confirming, start polling for status updates
      startPolling();
    } catch (err) {
      setResult({
        status: "error",
        message: err.response?.data?.detail || "Something went wrong. Please try again.",
      });
    } finally {
      setConfirming(false);
    }
  };

  if (loading) {
    return (
      <div className="retrieve-page" data-testid="retrieve-loading">
        <div className="retrieve-card">
          <div className="retrieve-spinner" />
          <p style={{ color: "#a1a1aa", marginTop: 16 }}>Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="retrieve-page" data-testid="retrieve-error">
        <div className="retrieve-card">
          <div className="retrieve-icon retrieve-icon-error">!</div>
          <h2 style={{ color: "#fff", margin: "16px 0 8px" }}>Not Found</h2>
          <p style={{ color: "#a1a1aa" }}>{error}</p>
        </div>
      </div>
    );
  }

  // Already checked out
  if (vehicle?.status === "checked_out") {
    return (
      <div className="retrieve-page" data-testid="retrieve-checked-out">
        <div className="retrieve-card">
          <div className="retrieve-icon retrieve-icon-done">&#10003;</div>
          <h2 style={{ color: "#fff", margin: "16px 0 8px" }}>Already Collected</h2>
          <p style={{ color: "#a1a1aa" }}>
            Your vehicle <strong>{vehicle.license_plate}</strong> has already been checked out.
          </p>
        </div>
      </div>
    );
  }

  // Show result only if no active ticket yet (first-time confirm)
  if (result && !vehicle?.active_ticket_status) {
    const isSuccess = result.status === "open";
    const isPending = result.status === "pending_payment";
    return (
      <div className="retrieve-page" data-testid="retrieve-result">
        <div className="retrieve-card">
          <div className={`retrieve-icon ${isSuccess ? "retrieve-icon-done" : isPending ? "retrieve-icon-pending" : "retrieve-icon-error"}`}>
            {isSuccess ? "\u2713" : isPending ? "\u20B9" : "!"}
          </div>
          <h2 style={{ color: "#fff", margin: "16px 0 8px" }}>
            {isSuccess ? "Request Confirmed!" : isPending ? "Payment Required" : "Notice"}
          </h2>
          <p style={{ color: "#a1a1aa", lineHeight: 1.5 }}>{result.message}</p>
        </div>
      </div>
    );
  }

  // Active ticket — show live status
  if (vehicle?.active_ticket_status) {
    const st = vehicle.active_ticket_status;
    return (
      <div className="retrieve-page" data-testid="retrieve-active-ticket">
        <div className="retrieve-card">
          <div className="retrieve-brand">VALET GUYS</div>

          <div className="retrieve-plate-box" style={{ marginTop: 16, fontSize: 20, padding: "10px 24px" }}>
            {vehicle.license_plate}
          </div>

          {/* Status: open */}
          {st === "open" && (
            <div className="retrieve-status-section" data-testid="retrieve-status-open">
              <div className="retrieve-icon retrieve-icon-active" style={{ width: 48, height: 48, fontSize: 20 }}>&#8635;</div>
              <h2 style={{ color: "#fff", margin: "12px 0 6px", fontSize: 18 }}>Waiting for Valet</h2>
              <p style={{ color: "#a1a1aa", fontSize: 14, lineHeight: 1.5 }}>
                Your request is active. A valet will pick it up shortly.
              </p>
              <div className="retrieve-pulse" />
            </div>
          )}

          {/* Status: claimed or en_route */}
          {(st === "claimed" || st === "en_route") && (
            <div className="retrieve-status-section" data-testid="retrieve-status-enroute">
              <div className="retrieve-icon retrieve-icon-active" style={{ width: 48, height: 48, fontSize: 22 }}>
                &#9654;
              </div>
              <h2 style={{ color: "#fff", margin: "12px 0 6px", fontSize: 18 }}>
                {vehicle.valet_name ? `${vehicle.valet_name} is on the way` : "Valet is on the way"}
              </h2>
              <p style={{ color: "#a1a1aa", fontSize: 14, lineHeight: 1.5 }}>
                Your car is being brought to the pickup area.
              </p>
              <div className="retrieve-pulse" />
            </div>
          )}

          {/* Status: arrived — show timer */}
          {st === "arrived" && (
            <div className="retrieve-status-section" data-testid="retrieve-status-arrived">
              <div className="retrieve-icon retrieve-icon-done" style={{ width: 48, height: 48, fontSize: 22 }}>
                &#10003;
              </div>
              <h2 style={{ color: "#22c55e", margin: "12px 0 6px", fontSize: 18 }}>
                Your Car is Here!
              </h2>
              <p style={{ color: "#a1a1aa", fontSize: 14, marginBottom: 16 }}>
                {vehicle.valet_name
                  ? `${vehicle.valet_name} has your car at the entrance.`
                  : "Your car is at the entrance."}
              </p>
              <CountdownTimer arrivedAt={vehicle.arrived_at} waitMinutes={vehicle.wait_timer || 5} />
            </div>
          )}

          {/* Status: pending_payment */}
          {st === "pending_payment" && (
            <div className="retrieve-status-section" data-testid="retrieve-status-pending">
              <div className="retrieve-icon retrieve-icon-pending" style={{ width: 48, height: 48, fontSize: 22 }}>
                &#8377;
              </div>
              <h2 style={{ color: "#f59e0b", margin: "12px 0 6px", fontSize: 18 }}>Payment Pending</h2>
              <p style={{ color: "#a1a1aa", fontSize: 14, lineHeight: 1.5 }}>
                Please complete your valet fee payment to proceed with retrieval.
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Main retrieval confirmation (no active ticket)
  return (
    <div className="retrieve-page" data-testid="retrieve-confirm-page">
      <div className="retrieve-card">
        <div className="retrieve-brand">PARKARO</div>
        <p style={{ color: "#71717a", fontSize: 12, letterSpacing: 2, marginBottom: 24 }}>
          {vehicle.client_name?.toUpperCase()}
        </p>

        <div className="retrieve-plate-box" data-testid="retrieve-license-plate">
          {vehicle.license_plate}
        </div>

        {vehicle.tag_number && (
          <p style={{ color: "#a1a1aa", fontSize: 14, marginTop: 8 }}>
            Tag #{vehicle.tag_number}
          </p>
        )}

        {vehicle.valet_fee > 0 && (
          <div className="retrieve-fee" data-testid="retrieve-fee-info">
            <span style={{ color: "#a1a1aa" }}>Valet Fee</span>
            <span style={{ color: "#fff", fontWeight: 700, fontSize: 20 }}>
              Rs.{vehicle.valet_fee}
            </span>
          </div>
        )}

        <button
          className="retrieve-btn"
          onClick={handleConfirm}
          disabled={confirming}
          data-testid="retrieve-confirm-button"
        >
          {confirming ? "Requesting..." : "Get My Car"}
        </button>

        <p style={{ color: "#52525b", fontSize: 12, marginTop: 16 }}>
          A valet will bring your car to the pickup area
        </p>
      </div>
    </div>
  );
}
