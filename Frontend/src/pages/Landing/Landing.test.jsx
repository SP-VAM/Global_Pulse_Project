import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import React from "react"
import { MemoryRouter } from "react-router-dom"
import Landing from "./Landing.jsx"

// Mock WebGL canvas to prevent THREE.js errors in JSDOM
vi.mock("./FinancialGalaxyCanvas", () => {
  return {
    default: () => <div data-testid="galaxy-canvas" />,
  }
})

// Mock IntersectionObserver which is missing in JSDOM
class IntersectionObserverMock {
  constructor(callback) {
    this.callback = callback
  }
  observe(node) {
    if (this.callback) {
      this.callback([{ isIntersecting: true }], this)
    }
  }
  unobserve() {}
  disconnect() {}
}
window.IntersectionObserver = IntersectionObserverMock

// Mock jsPDF to verify download behavior without throwing in JSDOM environment
const mockSave = vi.fn()
vi.mock("jspdf", () => {
  return {
    default: vi.fn().mockImplementation(() => ({
      internal: {
        pageSize: {
          getWidth: () => 595,
          getHeight: () => 842,
        },
        getNumberOfPages: () => 1,
      },
      setFont: vi.fn(),
      setFontSize: vi.fn(),
      setTextColor: vi.fn(),
      text: vi.fn(),
      setFillColor: vi.fn(),
      setDrawColor: vi.fn(),
      setLineWidth: vi.fn(),
      line: vi.fn(),
      roundedRect: vi.fn(),
      splitTextToSize: vi.fn((text) => [text]),
      addPage: vi.fn(),
      save: mockSave,
    })),
  }
})

describe("GlobalPulse Landing Page Actions and Modals Unit Tests - AC:1 to AC:11", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.body.className = ""
  })

  it("AC:1 – Create Free Account is displayed and clicking it opens/navigates to the Sign-Up/Registration flow", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    // Find the Create Free Account button
    const signUpBtn = screen.getByRole("button", { name: /Create Free Account/i })
    expect(signUpBtn).toBeInTheDocument()

    // Click button to open Sign Up Modal
    fireEvent.click(signUpBtn)

    // Confirm it opens sign up details
    expect(screen.getByText("Create an Account")).toBeInTheDocument()
  })

  it("AC:2 – Privacy is displayed and clicking it opens the Privacy Policy document", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    const privacyLink = screen.getByRole("button", { name: "Privacy" })
    expect(privacyLink).toBeInTheDocument()

    // Open Privacy policy modal
    fireEvent.click(privacyLink)
    expect(screen.getByRole("heading", { name: "Privacy Policy" })).toBeInTheDocument()
  })

  it("AC:3 – Privacy Policy download functionality works", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    const privacyLink = screen.getByRole("button", { name: "Privacy" })
    fireEvent.click(privacyLink)

    // Trigger PDF download
    const downloadBtn = screen.getByRole("button", { name: /Download PDF/i })
    expect(downloadBtn).toBeInTheDocument()
    fireEvent.click(downloadBtn)

    // Verify mock jsPDF save was triggered with correct filename
    expect(mockSave).toHaveBeenCalledTimes(1)
    expect(mockSave).toHaveBeenCalledWith("GlobalPulse_Privacy_Policy.pdf")
  })

  it("AC:4 – Terms is displayed and clicking it opens the Terms & Conditions document", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    const termsLink = screen.getByRole("button", { name: "Terms" })
    expect(termsLink).toBeInTheDocument()

    // Open Terms Modal
    fireEvent.click(termsLink)
    expect(screen.getByRole("heading", { name: "Terms & Conditions" })).toBeInTheDocument()
  })

  it("AC:5 – Terms & Conditions download functionality works", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    const termsLink = screen.getByRole("button", { name: "Terms" })
    fireEvent.click(termsLink)

    // Trigger PDF download
    const downloadBtn = screen.getByRole("button", { name: /Download PDF/i })
    expect(downloadBtn).toBeInTheDocument()
    fireEvent.click(downloadBtn)

    // Verify mock PDF file save
    expect(mockSave).toHaveBeenCalledTimes(1)
    expect(mockSave).toHaveBeenCalledWith("GlobalPulse_Terms___Conditions.pdf")
  })

  it("AC:6 – Disclaimer is displayed and clicking it opens the Disclaimer document", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    const disclaimerLink = screen.getByRole("button", { name: "Disclaimer" })
    expect(disclaimerLink).toBeInTheDocument()

    // Open Disclaimer Modal
    fireEvent.click(disclaimerLink)
    expect(screen.getByRole("heading", { name: "Financial & Application Disclaimer" })).toBeInTheDocument()
  })

  it("AC:7 – Disclaimer download functionality works", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    const disclaimerLink = screen.getByRole("button", { name: "Disclaimer" })
    fireEvent.click(disclaimerLink)

    // Trigger PDF download
    const downloadBtn = screen.getByRole("button", { name: /Download PDF/i })
    expect(downloadBtn).toBeInTheDocument()
    fireEvent.click(downloadBtn)

    // Verify PDF save
    expect(mockSave).toHaveBeenCalledTimes(1)
    expect(mockSave).toHaveBeenCalledWith("GlobalPulse_Financial___Application_Disclaimer.pdf")
  })

  it("AC:8 – Contact is displayed and clicking it opens the Contact Us popup", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    const contactLink = screen.getByRole("button", { name: "Contact" })
    expect(contactLink).toBeInTheDocument()

    // Open Contact modal
    fireEvent.click(contactLink)
    expect(screen.getByRole("heading", { name: "Contact Us" })).toBeInTheDocument()
  })

  it("AC:9 – Contact Us popup displays the configured GlobalPulse support email and contact information", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    const contactLink = screen.getByRole("button", { name: "Contact" })
    fireEvent.click(contactLink)

    // Verify Email and descriptions
    const emailLink = screen.getByRole("link", { name: "support@globalpulse.com" })
    expect(emailLink).toBeInTheDocument()
    expect(emailLink).toHaveAttribute("href", "mailto:support@globalpulse.com")
    expect(screen.getByText(/Need help or have questions/i)).toBeInTheDocument()
    expect(screen.getByText(/For technical assistance, account-related queries/i)).toBeInTheDocument()
  })

  it("AC:10 – Contact popup can be closed using the Close button or X icon", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    const contactLink = screen.getByRole("button", { name: "Contact" })
    
    // Test Close button closure
    fireEvent.click(contactLink)
    const closeBtn = screen.getByRole("button", { name: "Close" })
    fireEvent.click(closeBtn)
    expect(screen.queryByRole("heading", { name: "Contact Us" })).not.toBeInTheDocument()

    // Test X icon closure
    fireEvent.click(contactLink)
    const xBtn = screen.getByLabelText("Close dialog")
    fireEvent.click(xBtn)
    expect(screen.queryByRole("heading", { name: "Contact Us" })).not.toBeInTheDocument()
  })

  it("AC:11 – Contact popup does NOT contain Full Name, Email Address, Message or Send Message fields", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    const contactLink = screen.getByRole("button", { name: "Contact" })
    fireEvent.click(contactLink)

    // Confirm that the form fields and submit button are completely absent
    expect(screen.queryByLabelText(/Full Name/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/Email Address/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/Message/i)).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Send Message/i })).not.toBeInTheDocument()
  })
})
